"""文件夹自动候补排期核心服务（zh_overrides 本地定制，05:45 用户定稿）。

用户在帖子编辑器勾选平台账号、选定单个监听文件夹后「开启自动候补」：

* 无新增页面/设置项——配置动作只发生在作曲器弹窗；社交账号页仅有一个总开关。
* 后台每 10 分钟（1Panel 计划任务执行管理命令）扫描所有启用中的规则，使每个
  目标账号「未来 48 小时」内的空槽始终排满监听文件夹里 FIFO 最前的合格视频。
* 候选口径：仅监听文件夹本身（不含子文件夹；null=根目录散素材）、当前工作区、
  media_type=video、处理完成、时长合格、文件已落盘；图片/未处理素材静默排除。
* 一条视频一条 Post，每个目标账号各一个 PlatformPost，各账号独立占自己的
  未来 48 小时空槽（多账号同条视频在不同账号按各自时段发布）。
* 消耗账本 (social_account, media_asset) 唯一，失败/取消/清除/停用恢复/换
  文件夹都不重发；零上游改动，槽位/锁/队列/状态机全部复用上游零件。
* 每次实际投递生成一个批次（ZhScheduledBatch），供发布队列页「自动」标签
  一键清除；已发布（受保护状态）的历史帖不会被清除。
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

logger = logging.getLogger("zh_overrides.auto_schedule")

# 滚动候补窗口：未来 48 小时。
WINDOW_HOURS = 48
# 候选槽位展开上限：48h 内任何现实配置都不可能超过这个数。
_MAX_SLOT_CANDIDATES = 500

# 这些状态下视为"该视频在此账号上已有活跃帖"，不重复投递（账本之外的双保险）。
_ACTIVE_POST_STATUSES = ("scheduled", "publishing", "published")


class AutoScheduleError(Exception):
    """开启/恢复前置条件不满足（消息直接展示给用户，保持简短）。"""


def open_slot_datetimes(social_account, *, after=None, hours: int = WINDOW_HOURS):
    """该账号未来 ``hours`` 小时内尚未被占用的发帖时刻（升序）。

    与上游 ``_next_available_slot`` 同口径（PostingSlot 配置减去
    PlatformPost.scheduled_at 占用），区别仅在视界由 60 天收紧为 48h。
    """
    from apps.calendar.services import _next_slot_datetimes, _occupied_datetimes

    after = after or timezone.now()
    horizon = after + timedelta(hours=hours)
    candidates = _next_slot_datetimes(social_account, after, count=_MAX_SLOT_CANDIDATES)
    occupied = _occupied_datetimes(social_account)
    return [dt for dt in candidates if dt <= horizon and dt not in occupied]


def _completed_video_qs(workspace, folder_id, *, root=False):
    """监听目标内"处理完成且时长合格"的视频候选查询集（不含子文件夹）。

    口径：当前工作区、media_type=video、processing_status=completed、文件已
    落盘、duration>0。``root=True`` 时取未分文件夹（folder IS NULL）的根目录
    散素材；图片天然不在查询内（静默过滤）。
    """
    from apps.media_library.models import MediaAsset

    qs = (
        MediaAsset.objects.filter(
            workspace=workspace,
            media_type=MediaAsset.MediaType.VIDEO,
            processing_status=MediaAsset.ProcessingStatus.COMPLETED,
            duration__gt=0,
        )
        .exclude(file="")
    )
    return qs.filter(folder__isnull=True) if root else qs.filter(folder_id=folder_id)


def folder_video_counts(workspace, folders):
    """批量统计若干命名文件夹各自的合格视频数（文件夹格子角标用）。"""
    rows = (
        _completed_video_qs(workspace, None)
        .filter(folder__in=folders)
        .values("folder_id")
        .annotate(n=Count("id"))
    )
    return {row["folder_id"]: row["n"] for row in rows}


def root_video_count(workspace):
    """根目录（未分文件夹）合格视频数。"""
    return _completed_video_qs(workspace, None, root=True).count()


def resolve_targets(workspace, accounts):
    """解析勾选账号为 (targets, ignored)。

    targets = [(account, queue), ...]：连接正常、存在活动队列、能接受视频
    投稿的账号，按 id 排序以便固定加锁；ignored = [(name, reason)]。
    """
    from apps.calendar.models import Queue
    from apps.composer.services import media_blocker

    targets, ignored = [], []
    for account in sorted(accounts, key=lambda a: str(a.id)):
        name = account.account_name or account.account_handle or account.platform
        if getattr(account, "needs_reconnect", False):
            ignored.append((name, "disconnected"))
            continue
        queue = Queue.objects.filter(
            workspace=workspace, social_account=account, is_active=True
        ).first()
        if queue is None:
            ignored.append((name, "no queue"))
            continue
        if media_blocker(account, media_types={"video"}):
            ignored.append((name, "unsupported"))
            continue
        targets.append((account, queue))
    return targets, ignored


def rule_status(rule):
    """弹窗/开关展示数据：监听标签、已投递视频数、跳过账号列表。"""
    accounts = list(rule.accounts.all())
    _, ignored = resolve_targets(rule.workspace, accounts)
    delivered = rule.consumptions.values("media_asset_id").distinct().count()
    return {
        "is_active": rule.is_active,
        "folder_label": rule.folder_name or "媒体库根目录",
        "folder_missing": rule.folder_missing,
        "delivered": delivered,
        "ignored": [name for name, _reason in ignored],
    }


def enable_rule(*, workspace, user, folder, account_ids, form_snapshot):
    """开启或整单替换规则，成功后立即补排一次。返回 (rule, created_count)。

    已有规则 = 整单替换（更新同一行；账本保留，老视频不重发）。监听文件夹
    被删除的旧规则也可通过本接口重新选定目标后复活。
    """
    from apps.composer.services import _require_approval_gate_passes
    from apps.social_accounts.models import SocialAccount

    from .models import ZhAutoScheduleRule

    try:
        _require_approval_gate_passes(workspace)
    except ValueError as exc:
        raise AutoScheduleError(str(exc))

    accounts = list(
        SocialAccount.objects.filter(id__in=account_ids, workspace=workspace)
    )
    # M2M 保存全部勾选的本工作区账号（含当前断连/无队列的）：投递时再按
    # resolve_targets 跳过，账号恢复连接/建好队列后下轮自动纳入，无需重配。
    valid_targets, _ = resolve_targets(workspace, accounts)
    valid_ids = {account.id for account, _queue in valid_targets}
    if not valid_ids:
        raise AutoScheduleError("Select at least one valid account first.")

    fb_types = {}
    for account in accounts:
        if account.id not in valid_ids:
            continue
        value = (form_snapshot.get(f"facebook_post_type_{account.id}", "") or "").strip()
        if account.platform == "facebook" and value == "reel":
            fb_types[str(account.id)] = "reel"

    now = timezone.now()
    rule, _created = ZhAutoScheduleRule.objects.update_or_create(
        workspace=workspace,
        defaults={
            "media_folder": folder,
            "folder_name": folder.name[:255] if folder else "",
            "caption": form_snapshot.get("caption", "") or "",
            "first_comment": form_snapshot.get("first_comment", "") or "",
            "facebook_post_types": fb_types,
            "is_active": True,
            "enabled_at": now,
        },
    )
    rule.accounts.set(accounts)

    # 整单替换：旧批次标签保留为历史；本次开启立即补排第一批。
    created = run_rule(rule, user=user)
    return rule, created


def _create_one_post(*, rule, user, asset, targets, slot_lists):
    """调用方已持全部账号行锁；为一个视频建帖并写入各账号槽位+记账。"""
    from apps.calendar.services import _ensure_entry, _write_slot
    from apps.composer.models import PlatformPost, Post, PostMedia
    from apps.composer.services import sync_post_scheduled_at, transition_platform_post

    from .models import ZhAutoScheduleConsumption

    post = Post.objects.create(
        workspace=rule.workspace,
        author=user,  # 系统自动投递：作者为开启规则的用户；SET_NULL 亦安全
        caption=rule.caption,
        first_comment=rule.first_comment,
    )
    PostMedia.objects.create(post=post, media_asset=asset, position=0)

    consumptions = []
    for index, (account, queue) in enumerate(targets):
        platform_post = PlatformPost.objects.create(
            post=post,
            social_account=account,
            status=PlatformPost.Status.DRAFT,
            platform_extra=(
                {"post_type": "reel"}
                if rule.facebook_post_types.get(str(account.id)) == "reel"
                else {}
            ),
        )
        entry = _ensure_entry(post, queue)
        slot_dt = slot_lists[index][0]  # 调用方保证每个目标至少还有一个空槽
        _write_slot(entry, platform_post, slot_dt)
        transition_platform_post(platform_post, "scheduled", scheduled_at=slot_dt)
        slot_lists[index].pop(0)  # 本槽已占，下一视频取下一空槽
        consumptions.append(
            ZhAutoScheduleConsumption(
                rule=rule,
                social_account=account,
                media_asset=asset,
                post=post,
                platform_post=platform_post,
            )
        )
    sync_post_scheduled_at(post)
    ZhAutoScheduleConsumption.objects.bulk_create(consumptions)
    return post


def run_rule(rule, *, user=None):
    """补排一次，返回本轮新建帖子数。任何失败整体回滚，不留半截帖子。

    监听文件夹已删除（folder_missing）时自动停用，不投递。
    """
    from apps.social_accounts.models import SocialAccount

    from .models import ZhScheduledBatch, ZhScheduledBatchItem

    if not rule.is_active:
        return 0
    if rule.folder_missing:
        rule.is_active = False
        rule.save(update_fields=["is_active", "updated_at"])
        logger.warning("规则 %s 监听文件夹已删除，自动停用", rule.id)
        return 0

    root = rule.media_folder_id is None
    accounts = list(rule.accounts.all())
    targets, ignored = resolve_targets(rule.workspace, accounts)
    if not targets:
        rule.last_run_at = timezone.now()
        rule.save(update_fields=["last_run_at"])
        return 0

    from apps.composer.models import PlatformPost

    with transaction.atomic():
        list(
            SocialAccount.objects.select_for_update()
            .filter(id__in=[account.id for account, _q in targets])
            .order_by("id")
        )
        slot_lists = [open_slot_datetimes(account) for account, _q in targets]
        min_slots = min((len(slots) for slots in slot_lists), default=0)
        if min_slots <= 0:
            rule.last_run_at = timezone.now()
            rule.save(update_fields=["last_run_at"])
            return 0

        # 候选视频：监听目标 FIFO，排除账本（同账号已投递）与活跃帖。
        from .models import ZhAutoScheduleConsumption

        target_accounts = [account for account, _q in targets]
        consumed_ids = ZhAutoScheduleConsumption.objects.filter(
            social_account__in=target_accounts
        ).values_list("media_asset_id", flat=True)
        active_asset_ids = (
            PlatformPost.objects.filter(
                social_account__in=target_accounts,
                status__in=_ACTIVE_POST_STATUSES,
            )
            .values_list("post__media_attachments__media_asset_id", flat=True)
            .distinct()
        )
        assets = list(
            _completed_video_qs(rule.workspace, rule.media_folder_id, root=root)
            .exclude(id__in=list(consumed_ids))
            .exclude(id__in=list(active_asset_ids))
            .order_by("created_at", "id")
        )
        n = min(len(assets), min_slots)
        if n == 0:
            rule.last_run_at = timezone.now()
            rule.save(update_fields=["last_run_at"])
            return 0

        chosen = assets[:n]
        posts = [
            _create_one_post(
                rule=rule, user=user, asset=asset, targets=targets,
                slot_lists=slot_lists,
            )
            for asset in chosen
        ]

        batch = ZhScheduledBatch.objects.create(
            workspace=rule.workspace,
            rule=rule,
            media_folder=rule.media_folder,
            folder_name=rule.folder_name,
            created_by=user,
        )
        ZhScheduledBatchItem.objects.bulk_create(
            ZhScheduledBatchItem(batch=batch, post=post, media_asset=asset)
            for post, asset in zip(posts, chosen)
        )
        rule.last_run_at = timezone.now()
        rule.save(update_fields=["last_run_at"])

    logger.info(
        "自动候补：规则 %s 工作区 %s 新建 %d 条 / %d 账号（忽略 %d 账号）",
        rule.id, rule.workspace_id, n, len(targets), len(ignored),
    )
    return n


def run_all_active_rules():
    """管理命令入口：遍历全部启用规则。返回总投递数。"""
    from .models import ZhAutoScheduleRule

    total = 0
    for rule in ZhAutoScheduleRule.objects.filter(is_active=True).prefetch_related(
        "accounts"
    ):
        try:
            total += run_rule(rule)
        except Exception:
            logger.exception("自动候补规则 %s 处理异常", rule.id)
    return total


def active_batches(workspace):
    """队列页「自动」标签数据：仍有 scheduled 帖子的批次（新→旧）。"""
    from .models import ZhScheduledBatch

    return list(
        ZhScheduledBatch.objects.filter(workspace=workspace)
        .annotate(
            remaining=Count(
                "items",
                filter=Q(items__post__platform_posts__status="scheduled"),
                distinct=True,
            )
        )
        .filter(remaining__gt=0)
        .order_by("-created_at")
    )


def clear_batch(batch) -> int:
    """一键清除批次内仍可删除的帖子，返回删除条数。

    含 published/publishing（受保护状态）子帖的 Post 保留为历史；其余帖子
    CASCADE 删除（PlatformPost/QueueEntry/批次明细/账本中该账号记录随之清
    除——账本按 (账号,视频) 唯一，删除后该视频可被规则重新取用补位）。
    """
    from apps.composer.models import PlatformPost, Post

    with transaction.atomic():
        posts = list(batch.items.values_list("post", flat=True))
        protected = set(
            PlatformPost.objects.filter(post_id__in=posts)
            .filter(status__in=PlatformPost.PROTECTED_STATUSES)
            .values_list("post_id", flat=True)
        )
        deletable = [pid for pid in posts if pid not in protected]
        if deletable:
            Post.objects.filter(id__in=deletable).delete()
        logger.info("批次 %s 一键清除：删除 %d 条帖子", batch.id, len(deletable))
        return len(deletable)
