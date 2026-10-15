"""作曲器「文件夹」模式一键批量入队核心服务（zh_overrides 本地定制）。

用户确认的方案（2026-10-15）：

* 无持久规则、无后台任务、无社交页开关——一切在作曲器页面一次点击内同步完成。
* 单一文件夹（不含子文件夹）；只统计当前工作区"处理完成且时长合格"的视频，
  图片与未处理完成素材静默排除；按上传时间 FIFO 取前 N 个。
* 一条视频建一条 Post，每条勾选账号各建一个 PlatformPost；各账号独立占用
  自己未来 7 天的空闲时段（上游 PostingSlot/Queue 原生语义）。
* 数量步进器默认值 = 各勾选账号未来 7 天空槽数的最小值（同时不超过可用视频数）。
* 活跃帖反查：在任一勾选账号上已有 scheduled/publishing/published 帖子的视频
  不再重复入队。
* 零上游改动：槽位/锁/队列/状态机全部复用 apps.calendar.services 与
  apps.composer.services 的现成零件，仅在覆盖层包一层 7 天视界。
* 入队结果以批次（ZhScheduledBatch）落账，供发布队列页一键批量清除；
  已发布（受保护状态）的历史帖不会被清除。
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

logger = logging.getLogger("zh_overrides.batch_schedule")

# 入队视界：未来 7 天。
WINDOW_HOURS = 7 * 24
# 候选槽位展开上限：7 天内任何现实配置都不可能超过这个数。
_MAX_SLOT_CANDIDATES = 500
# 单次入队硬上限，防止异常请求一次建帖过多。
MAX_BATCH_COUNT = 200

# 这些状态下视为"该视频在此账号上已有活跃帖"，不再重复投递。
_ACTIVE_POST_STATUSES = ("scheduled", "publishing", "published")


class BatchScheduleError(Exception):
    """入队前置条件不满足（消息直接展示给用户，需保持简短中文可译）。"""


def open_slot_datetimes(social_account, *, after=None, hours: int = WINDOW_HOURS):
    """该账号未来 ``hours`` 小时内尚未被占用的发帖时刻（升序）。

    与上游 ``_next_available_slot`` 同口径（PostingSlot 配置减去
    PlatformPost.scheduled_at 占用），区别仅在视界由 60 天收紧为 7 天。
    """
    # 函数内导入保持"覆盖层只引用、不修改"的边界，同时便于测试 monkeypatch。
    from apps.calendar.services import _next_slot_datetimes, _occupied_datetimes

    after = after or timezone.now()
    horizon = after + timedelta(hours=hours)
    candidates = _next_slot_datetimes(social_account, after, count=_MAX_SLOT_CANDIDATES)
    occupied = _occupied_datetimes(social_account)
    return [dt for dt in candidates if dt <= horizon and dt not in occupied]


def _completed_video_qs(workspace, folder=None):
    """当前工作区"处理完成且时长合格"的视频候选查询集。

    口径：media_type=video、processing_status=completed、文件已落盘、
    duration>0。0 秒通常是还没处理完成或无法解析时长的素材，直接排掉可以
    避免发布到平台才失败；图片天然不在查询内（静默过滤）。``folder`` 给定时
    仅该文件夹本身（不含子文件夹）。
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
    if folder is not None:
        qs = qs.filter(folder=folder)
    return qs


def eligible_assets(workspace, folder, accounts):
    """可入队视频 FIFO（早上传在前）：排除在任一目标账号上已有活跃帖的视频。"""
    from apps.composer.models import PlatformPost

    active_asset_ids = (
        PlatformPost.objects.filter(
            social_account__in=accounts,
            status__in=_ACTIVE_POST_STATUSES,
        )
        .values_list("post__media_attachments__media_asset_id", flat=True)
        .distinct()
    )
    return list(
        _completed_video_qs(workspace, folder)
        .exclude(id__in=list(active_asset_ids))
        .order_by("created_at", "id")
    )


def folder_video_counts(workspace, folders):
    """批量统计若干文件夹各自的合格视频数（用于文件夹浏览格子角标）。"""
    from apps.media_library.models import MediaAsset

    rows = (
        _completed_video_qs(workspace, None)
        .filter(folder__in=folders)
        .values("folder_id")
        .annotate(n=Count("id"))
    )
    return {row["folder_id"]: row["n"] for row in rows}


def resolve_targets(workspace, account_ids):
    """解析勾选账号为 (targets, ignored)。

    targets = [(account, queue), ...]：连接正常、存在活动队列、且能接受视频
    投稿的账号（Pinterest 无画板等确定性会失败的账号在这里剔除），按账号 id
    排序以便后续以固定顺序加锁。ignored = [(name, reason_en), ...]。
    """
    from apps.calendar.models import Queue
    from apps.composer.services import media_blocker
    from apps.social_accounts.models import SocialAccount

    accounts = list(
        SocialAccount.objects.filter(id__in=account_ids, workspace=workspace).order_by("id")
    )
    targets, ignored = [], []
    for account in accounts:
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
        reason = media_blocker(account, media_types={"video"})
        if reason:
            ignored.append((name, "unsupported"))
            continue
        targets.append((account, queue))
    return targets, ignored


def build_plan(workspace, folder, account_ids):
    """返回步进器预览：合格视频数、各账号 7 天空槽数与默认数量。"""
    targets, ignored = resolve_targets(workspace, account_ids)
    slots_by_account = {
        str(account.id): len(open_slot_datetimes(account)) for account, _queue in targets
    }
    min_slots = min(slots_by_account.values(), default=0)
    assets = eligible_assets(workspace, folder, [account for account, _q in targets])
    default_count = min(len(assets), min_slots)
    return {
        "eligible": len(assets),
        "slots": slots_by_account,
        "min_slots": min_slots,
        "default": default_count,
        "ignored_accounts": [
            {"name": name, "reason": reason} for name, reason in ignored
        ],
    }


def _facebook_extras(account, request_post):
    """读取该 FB 账号在作曲器页面的 Reel 选择快照（与上游作曲器同口径）。"""
    if account.platform != "facebook":
        return {}
    value = (request_post.get(f"facebook_post_type_{account.id}", "") or "").strip()
    return {"post_type": "reel"} if value == "reel" else {}


def _create_one_post(*, workspace, user, asset, targets, slot_lists, caption, first_comment, fb_extras):
    """在调用方已持有全部账号行锁的前提下，为一个视频建帖并写入各账号槽位。"""
    from apps.calendar.services import _ensure_entry, _write_slot
    from apps.composer.models import PlatformPost, Post, PostMedia
    from apps.composer.services import sync_post_scheduled_at, transition_platform_post

    post = Post.objects.create(
        workspace=workspace,
        author=user,
        caption=caption,
        first_comment=first_comment,
    )
    PostMedia.objects.create(post=post, media_asset=asset, position=0)

    for index, (account, queue) in enumerate(targets):
        platform_post = PlatformPost.objects.create(
            post=post,
            social_account=account,
            status=PlatformPost.Status.DRAFT,
            platform_extra=fb_extras.get(account.id, {}),
        )
        entry = _ensure_entry(post, queue)
        slot_dt = slot_lists[index][0]  # 调用方保证每个目标至少还有一个空槽
        _write_slot(entry, platform_post, slot_dt)
        # draft → scheduled：内含审批门与可发布性校验，与手动入队完全同路径。
        transition_platform_post(platform_post, "scheduled", scheduled_at=slot_dt)
        # 该槽已被占用，弹出，保证同一账号下一条视频取下一个空槽。
        slot_lists[index].pop(0)
    sync_post_scheduled_at(post)
    return post


def enqueue_batch(
    *,
    workspace,
    user,
    folder,
    account_ids,
    count,
    caption="",
    first_comment="",
    facebook_post_types=None,
):
    """一键批量入队。返回 (batch, created_count)。

    全部帖子在单个事务内创建，并一次性锁定所有目标账号行；锁内重算 7 天空槽，
    实际入队数 = min(请求数量, 合格视频数, 各账号空槽最小值)，任何失败整体
    回滚，不留半截帖子。
    """
    from apps.composer.services import _require_approval_gate_passes
    from apps.social_accounts.models import SocialAccount

    from .models import ZhScheduledBatch, ZhScheduledBatchItem

    # 审批门：开启了阻止直接排期审批流的工作区不允许批量入队（与上游
    # add_to_queue/手动 scheduled 转换的门禁一致）。
    try:
        _require_approval_gate_passes(workspace)
    except ValueError as exc:
        raise BatchScheduleError(str(exc))

    try:
        count = int(count)
    except (TypeError, ValueError):
        raise BatchScheduleError("Invalid quantity.")
    if count <= 0:
        raise BatchScheduleError("Invalid quantity.")
    count = min(count, MAX_BATCH_COUNT)

    if not account_ids:
        raise BatchScheduleError("Select at least one account first.")

    targets, ignored = resolve_targets(workspace, account_ids)
    if not targets:
        raise BatchScheduleError("No selected account can accept video posts right now.")

    fb_input = facebook_post_types or {}
    fb_extras = {account.id: _facebook_extras(account, fb_input) for account, _q in targets}

    with transaction.atomic():
        # 固定顺序锁住所有目标账号行：与并发手动操作/其他批量互不撞车。
        list(
            SocialAccount.objects.select_for_update()
            .filter(id__in=[account.id for account, _q in targets])
            .order_by("id")
        )
        # 锁内重算空槽（视界 7 天）。
        slot_lists = [open_slot_datetimes(account) for account, _q in targets]
        min_slots = min((len(slots) for slots in slot_lists), default=0)
        if min_slots <= 0:
            raise BatchScheduleError(
                "No open posting slot within 7 days for the selected accounts."
            )

        assets = eligible_assets(workspace, folder, [account for account, _q in targets])
        if not assets:
            raise BatchScheduleError("No eligible videos in this folder.")

        n = min(count, len(assets), min_slots)
        chosen = assets[:n]

        batch = ZhScheduledBatch.objects.create(
            workspace=workspace,
            media_folder=folder,
            folder_name=folder.name[:255],
            created_by=user,
        )

        posts = []
        for asset in chosen:
            post = _create_one_post(
                workspace=workspace,
                user=user,
                asset=asset,
                targets=targets,
                slot_lists=slot_lists,
                caption=caption or "",
                first_comment=first_comment or "",
                fb_extras=fb_extras,
            )
            posts.append(post)

        ZhScheduledBatchItem.objects.bulk_create(
            [
                ZhScheduledBatchItem(batch=batch, post=post, media_asset=asset)
                for post, asset in zip(posts, chosen)
            ]
        )

    logger.info(
        "批量入队：工作区 %s 文件夹 %s 新建 %d 条帖子 / %d 个账号（忽略 %d 个账号）",
        workspace.id,
        folder.id,
        n,
        len(targets),
        len(ignored),
    )
    return batch, n


def active_batches(workspace):
    """队列页批次条数据：仍有 scheduled 帖子的批次（新→旧）。"""
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

    含 published/publishing（受保护状态）子帖的 Post 保留为历史，只删除其余
    全部帖子（CASCADE 同步清掉 PlatformPost / QueueEntry / 批次明细），
    释放出来的发帖时段立即可重新使用。
    """
    from apps.composer.models import PlatformPost

    with transaction.atomic():
        posts = list(batch.items.values_list("post", flat=True))
        protected_post_ids = set(
            PlatformPost.objects.filter(post_id__in=posts)
            .filter(status__in=PlatformPost.PROTECTED_STATUSES)
            .values_list("post_id", flat=True)
        )
        deletable = [pid for pid in posts if pid not in protected_post_ids]
        if deletable:
            from apps.composer.models import Post

            Post.objects.filter(id__in=deletable).delete()
            logger.info("批次 %s 一键清除：删除 %d 条帖子", batch.id, len(deletable))
        return len(deletable)
