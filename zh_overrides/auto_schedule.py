"""文件夹自动排期核心服务（zh_overrides 本地定制，V2：24h + 武装开关）。

交互：用户在作曲器勾选平台账号、选定单个媒体文件夹后点原生「加入队列」
（拦截后走 /zh-auto/queue/），系统把该文件夹内 FIFO 最前的合格视频持续排满
每个目标账号「未来 24 小时」的空闲发帖时段，由 1Panel 计划任务每 10 分钟
补货。社交账号页「自动排期」总开关只做武装（开=允许使用；关=停止补货且
不自动恢复），不承载任何配置。

关键口径：
* 候选：仅监听文件夹本身（不含子文件夹；null=根目录散素材）、当前工作区、
  media_type=video、处理完成、时长合格、文件已落盘；图片/未处理素材静默排除。
* 一条视频一条 Post，每个目标账号各一个 PlatformPost、各占各账号自己的
  未来 24h 空槽（多账号同条视频按各自时段独立发布）。
* 消耗账本 (social_account, media_asset) 唯一，失败/取消/清除/停用/重开/
  换文件夹都不重发；零上游改动，槽位/锁/队列/状态机复用上游零件。
* 每次实际投递生成一个批次（ZhScheduledBatch），供发布队列页「自动」标签
  一键清除；已发布（受保护状态）的历史帖不会被清除。
* 性能：Post / PostMedia / PlatformPost / QueueEntry / 账本 / 明细全部
  bulk_create，避免逐条 insert 与逐条 transition 的 N+1。
"""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Max, Q
from django.utils import timezone

logger = logging.getLogger("zh_overrides.auto_schedule")

# 滚动候补窗口：未来 24 小时。
WINDOW_HOURS = 24
# 候选槽位展开上限：24h 内任何现实配置都远达不到这个数。
_MAX_SLOT_CANDIDATES = 300

# 该状态下视为"该视频在此工作区已有活跃帖"，不重复投递（账本之外的双保险）。
_ACTIVE_POST_STATUSES = ("scheduled", "publishing", "published")


class AutoScheduleError(Exception):
    """前置条件不满足（消息直接展示给用户，保持简短）。"""


def _meta(workspace):
    """获取（必要时创建）工作区旁路元数据行（武装开关载体）。"""
    from .models import WorkspaceMeta

    meta, _ = WorkspaceMeta.objects.get_or_create(workspace=workspace)
    return meta


def is_armed(workspace) -> bool:
    """工作区级「自动排期」总开关是否开启。"""
    return _meta(workspace).auto_schedule_armed


def set_armed(workspace, armed: bool) -> bool:
    """翻转武装开关，返回新值。

    关闭时同时停用规则（停止补货；已排入队列的帖子/账本一律不动）。开启时
    只武装，不恢复任何排期——用户必须重新在作曲器选文件夹+加入队列。
    """
    from .models import ZhAutoScheduleRule

    meta = _meta(workspace)
    meta.auto_schedule_armed = armed
    meta.save(update_fields=["auto_schedule_armed", "updated_at"])
    if not armed:
        ZhAutoScheduleRule.objects.filter(workspace=workspace, is_active=True).update(
            is_active=False, updated_at=timezone.now()
        )
    return armed


def open_slot_datetimes(social_account, *, after=None, hours: int = WINDOW_HOURS):
    """该账号未来 ``hours`` 小时内尚未被占用的发帖时刻（升序）。

    与上游同口径（PostingSlot 配置减去 PlatformPost.scheduled_at 占用），
    区别仅在视界由 60 天收紧为 24h。
    """
    from apps.calendar.services import _next_slot_datetimes, _occupied_datetimes

    after = after or timezone.now()
    horizon = after + timedelta(hours=hours)
    candidates = _next_slot_datetimes(social_account, after, count=_MAX_SLOT_CANDIDATES)
    occupied = _occupied_datetimes(social_account)
    return [dt for dt in candidates if dt <= horizon and dt not in occupied]


def _completed_video_base(workspace):
    """工作区内"处理完成且时长合格"的视频候选查询集（图片天然不在内）。"""
    from apps.media_library.models import MediaAsset

    return MediaAsset.objects.filter(
        workspace=workspace,
        media_type=MediaAsset.MediaType.VIDEO,
        processing_status=MediaAsset.ProcessingStatus.COMPLETED,
        duration__gt=0,
    ).exclude(file="")


def _completed_video_qs(workspace, folder_id, *, root=False):
    """监听目标内"处理完成且时长合格"的视频候选查询集（不含子文件夹）。

    ``root=True`` 时取未分文件夹（folder IS NULL）的根目录散素材。
    """
    qs = _completed_video_base(workspace)
    return qs.filter(folder__isnull=True) if root else qs.filter(folder_id=folder_id)


def _active_asset_ids(workspace):
    """该工作区内已存在活跃帖（scheduled/publishing/published）的视频素材 id。"""
    from apps.composer.models import PlatformPost

    return set(
        PlatformPost.objects.filter(
            post__workspace=workspace,
            status__in=_ACTIVE_POST_STATUSES,
        )
        .values_list("post__media_attachments__media_asset_id", flat=True)
        .distinct()
    )


def folder_video_counts(workspace, folders):
    """若干命名文件夹各自的"可排期视频数"（排除已有活跃帖的）。"""
    active = _active_asset_ids(workspace)
    rows = (
        _completed_video_base(workspace)
        .filter(folder__in=folders)
        .exclude(id__in=list(active))
        .values("folder_id")
        .annotate(n=Count("id"))
    )
    return {row["folder_id"]: row["n"] for row in rows}


def root_video_count(workspace):
    """根目录（未分文件夹）可排期视频数。"""
    return (
        _completed_video_qs(workspace, None, root=True)
        .exclude(id__in=list(_active_asset_ids(workspace)))
        .count()
    )


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
    """队列提交后的轻量状态（监听标签、已投递数、跳过账号）。"""
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


def submit_folder_schedule(*, workspace, user, folder, account_ids, form_snapshot):
    """创建/整单替换规则并立即补满 24h。返回 (rule, queued_count)。

    前置：工作区武装开关已开启。已有规则 = 整单替换（更新同一行；账本保留，
    老视频不重发）。监听文件夹被删除的旧规则也可通过本接口重新选定目标复活。
    """
    from apps.composer.services import _require_approval_gate_passes
    from apps.social_accounts.models import SocialAccount

    from .models import ZhAutoScheduleRule

    if not is_armed(workspace):
        raise AutoScheduleError("Enable auto-schedule in workspace settings first.")

    try:
        _require_approval_gate_passes(workspace)
    except ValueError as exc:
        raise AutoScheduleError(str(exc)) from None

    accounts = list(
        SocialAccount.objects.filter(id__in=account_ids, workspace=workspace)
    )
    valid_targets, _ignored = resolve_targets(workspace, accounts)
    valid_ids = {account.id for account, _queue in valid_targets}
    if not valid_ids:
        raise AutoScheduleError("Select at least one valid account first.")

    # Facebook 形态快照：仅记录显式 Reel；缺省即普通视频（与源码默认一致）。
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

    queued = run_rule(rule, user=user)
    return rule, queued


def run_rule(rule, *, user=None):
    """补排一次，返回本轮新建帖子数。任何失败整体回滚，不留半截帖子。

    监听文件夹已删除（folder_missing）或工作区武装开关关闭时自动停用。
    采用批量创建，避免逐条 insert/transition 的 N+1。
    """
    from apps.calendar.models import QueueEntry
    from apps.composer.models import PlatformPost, Post, PostMedia
    from apps.social_accounts.models import SocialAccount

    from .models import ZhAutoScheduleConsumption, ZhScheduledBatch, ZhScheduledBatchItem

    armed = is_armed(rule.workspace)
    if not rule.is_active:
        logger.info("自动排期跳过：规则 %s 未启用（工作区 %s）", rule.id, rule.workspace_id)
        return 0
    if rule.folder_missing or not armed:
        logger.info(
            "自动排期停用：规则 %s 文件夹已删=%s 总开关=%s（工作区 %s）",
            rule.id, rule.folder_missing, armed, rule.workspace_id,
        )
        rule.is_active = False
        rule.save(update_fields=["is_active", "updated_at"])
        return 0

    root = rule.media_folder_id is None
    accounts = list(rule.accounts.all())
    targets, ignored = resolve_targets(rule.workspace, accounts)
    if not targets:
        logger.info(
            "自动排期跳过：规则 %s 无可用目标账号，忽略=%s（工作区 %s）",
            rule.id, ignored, rule.workspace_id,
        )
        rule.last_run_at = timezone.now()
        rule.save(update_fields=["last_run_at"])
        return 0

    with transaction.atomic():
        list(
            SocialAccount.objects.select_for_update()
            .filter(id__in=[account.id for account, _queue in targets])
            .order_by("id")
        )
        slot_lists = [open_slot_datetimes(account) for account, _queue in targets]
        min_slots = min((len(slots) for slots in slot_lists), default=0)
        if min_slots <= 0:
            logger.info(
                "自动排期跳过：规则 %s 未来 %d 小时无空槽，各账号空槽数=%s（工作区 %s）",
                rule.id, WINDOW_HOURS, [len(s) for s in slot_lists], rule.workspace_id,
            )
            rule.last_run_at = timezone.now()
            rule.save(update_fields=["last_run_at"])
            return 0

        # 候选视频：监听目标 FIFO，排除账本（同账号已投递）与工作区活跃帖。
        target_accounts = [account for account, _queue in targets]
        consumed_ids = ZhAutoScheduleConsumption.objects.filter(
            social_account__in=target_accounts
        ).values_list("media_asset_id", flat=True)
        active_ids = _active_asset_ids(rule.workspace)
        assets = list(
            _completed_video_qs(rule.workspace, rule.media_folder_id, root=root)
            .exclude(id__in=list(consumed_ids))
            .exclude(id__in=list(active_ids))
            .order_by("created_at", "id")
        )
        n = min(len(assets), min_slots)
        if n == 0:
            logger.info(
                "自动排期跳过：规则 %s 无可排视频，空槽=%d 候选=%d 已消费=%d 活跃=%d（工作区 %s）",
                rule.id, min_slots, len(assets), len(consumed_ids), len(active_ids), rule.workspace_id,
            )
            rule.last_run_at = timezone.now()
            rule.save(update_fields=["last_run_at"])
            return 0

        chosen = assets[:n]

        # 1) Post（scheduled_at = 各账号槽位的最小值，替代逐条 sync_post_scheduled_at）。
        posts = []
        post_media = []
        for i, asset in enumerate(chosen):
            post = Post(
                id=uuid.uuid4(),
                workspace=rule.workspace,
                author=user,
                caption=rule.caption,
                first_comment=rule.first_comment,
                scheduled_at=min(slot_lists[j][i] for j in range(len(targets))),
            )
            posts.append(post)
            post_media.append(PostMedia(id=uuid.uuid4(), post=post, media_asset=asset, position=0))
        Post.objects.bulk_create(posts)
        PostMedia.objects.bulk_create(post_media)

        # 2) PlatformPost：直接落 scheduled（等价 draft 创建 + transition_to("scheduled")）。
        pp_objs = []
        for i, _asset in enumerate(chosen):
            for j, (account, _queue) in enumerate(targets):
                slot_dt = slot_lists[j][i]
                pp_objs.append(
                    PlatformPost(
                        id=uuid.uuid4(),
                        post=posts[i],
                        social_account=account,
                        status=PlatformPost.Status.SCHEDULED,
                        scheduled_at=slot_dt,
                        platform_extra=(
                            {"post_type": "reel"}
                            if rule.facebook_post_types.get(str(account.id)) == "reel"
                            else {}
                        ),
                    )
                )
        PlatformPost.objects.bulk_create(pp_objs)

        # 3) QueueEntry + 账本（按 (post_i, account_j) 对齐）。
        max_pos_map = {
            queue.id: (queue.entries.aggregate(m=Max("position"))["m"] or 0)
            for _account, queue in targets
        }
        entries = []
        consumptions = []
        idx = 0
        for i, asset in enumerate(chosen):
            for j, (account, queue) in enumerate(targets):
                pp = pp_objs[idx]
                idx += 1
                slot_dt = slot_lists[j][i]
                entries.append(
                    QueueEntry(
                        id=uuid.uuid4(),
                        queue=queue,
                        post=posts[i],
                        position=max_pos_map[queue.id] + i + 1,
                        assigned_slot_datetime=slot_dt,
                    )
                )
                consumptions.append(
                    ZhAutoScheduleConsumption(
                        id=uuid.uuid4(),
                        rule=rule,
                        social_account=account,
                        media_asset=asset,
                        post=posts[i],
                        platform_post=pp,
                    )
                )
        QueueEntry.objects.bulk_create(entries)
        ZhAutoScheduleConsumption.objects.bulk_create(consumptions)

        # 4) 批次 + 明细。
        batch = ZhScheduledBatch.objects.create(
            id=uuid.uuid4(),
            workspace=rule.workspace,
            rule=rule,
            media_folder=rule.media_folder,
            folder_name=rule.folder_name,
            created_by=user,
        )
        ZhScheduledBatchItem.objects.bulk_create(
            ZhScheduledBatchItem(id=uuid.uuid4(), batch=batch, post=post, media_asset=asset)
            for post, asset in zip(posts, chosen, strict=True)
        )
        rule.last_run_at = timezone.now()
        rule.save(update_fields=["last_run_at"])

    logger.info(
        "自动排期：规则 %s 工作区 %s 新建 %d 条 / %d 账号（忽略 %d 账号）",
        rule.id, rule.workspace_id, n, len(targets), len(ignored),
    )
    return n


def explain_zero(rule) -> str:
    """解释一次补排为什么返回 0（供前台在 queued_now=0 时展示原因）。

    只读诊断，复用与 ``run_rule`` 相同的判定顺序，返回面向用户的中文原因。
    """
    from .models import ZhAutoScheduleConsumption

    if not rule.is_active:
        return "自动排期已停用"
    if rule.folder_missing:
        return "监听文件夹已被删除，请回到编辑器重新选择"
    if not is_armed(rule.workspace):
        return "请先在社交账号页开启「自动排期」总开关"

    accounts = list(rule.accounts.all())
    targets, _ignored = resolve_targets(rule.workspace, accounts)
    if not targets:
        return "没有可用的目标账号（需已连接且有发帖队列）"

    slot_lists = [open_slot_datetimes(account) for account, _queue in targets]
    if min((len(slots) for slots in slot_lists), default=0) <= 0:
        return "未来 24 小时没有空闲发帖时段，请先在社交账号页添加发帖时段"

    target_accounts = [account for account, _queue in targets]
    consumed_ids = ZhAutoScheduleConsumption.objects.filter(
        social_account__in=target_accounts
    ).values_list("media_asset_id", flat=True)
    active_ids = _active_asset_ids(rule.workspace)
    root = rule.media_folder_id is None
    remaining = (
        _completed_video_qs(rule.workspace, rule.media_folder_id, root=root)
        .exclude(id__in=list(consumed_ids))
        .exclude(id__in=list(active_ids))
    )
    if not remaining.exists():
        return "该文件夹没有可排期的视频（已全部投递过，或时长无效 / 处理未完成）"
    return "没有可排期内容"


def run_all_active_rules():
    """管理命令入口：遍历武装开启 且 规则启用的工作区。返回总投递数。"""
    from .models import ZhAutoScheduleRule

    total = 0
    qs = ZhAutoScheduleRule.objects.filter(
        is_active=True,
        workspace__workspace_meta__auto_schedule_armed=True,
    ).prefetch_related("accounts")
    for rule in qs:
        try:
            total += run_rule(rule)
        except Exception:
            logger.exception("自动排期规则 %s 处理异常", rule.id)
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
