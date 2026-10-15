"""作曲器批量入队（文件夹模式）的视图层（zh_overrides 本地定制）。

端点全部挂在工作区前缀下，复用上游作曲器的工作区成员校验
（``apps.composer.views._get_workspace``）与成员权限装饰器，不复制鉴权逻辑。
除文件夹浏览片段走 htmx 交换外，预览/入队/批次操作均返回 JSON，由
zh_overrides 注入的 batch-schedule.js 驱动。
"""

from __future__ import annotations

import uuid

from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

# 复用上游成员校验与账号解析，避免再造一套 workspace 鉴权。
from apps.composer.views import _get_workspace, _parse_selected_account_ids
from apps.media_library.models import MediaFolder
from apps.members.decorators import require_permission

from . import batch_schedule
from .batch_schedule import BatchScheduleError
from .models import ZhScheduledBatch

_TEMPLATE_DIR = "zh_overrides/batch_schedule/"


def _folder_chain(folder):
    """从根到当前文件夹的面包屑链。"""
    chain = []
    current = folder
    while current is not None:
        chain.append(current)
        current = current.parent_folder
    return list(reversed(chain))


def _parse_uuid(raw):
    try:
        return uuid.UUID(str(raw))
    except (ValueError, TypeError, AttributeError):
        return None


@require_GET
@require_permission("create_posts")
def folders(request, workspace_id):
    """文件夹浏览片段：根级或指定父文件夹内的子文件夹网格。"""
    workspace = _get_workspace(request, workspace_id)
    parent = None
    raw_parent = request.GET.get("parent", "").strip()
    if raw_parent:
        parent = get_object_or_404(MediaFolder, id=raw_parent, workspace=workspace)

    qs = (
        MediaFolder.objects.filter(workspace=workspace, parent_folder=parent)
        .annotate(sub_count=Count("subfolders", distinct=True))
        .order_by("name")
    )
    folders = list(qs)
    video_counts = batch_schedule.folder_video_counts(workspace, folders)
    for folder in folders:
        folder.zh_video_count = video_counts.get(folder.id, 0)

    return render(
        request,
        _TEMPLATE_DIR + "_folder_grid.html",
        {
            "workspace": workspace,
            "folders": folders,
            "parent": parent,
            "chain": _folder_chain(parent) if parent else [],
        },
    )


def _parse_folder(workspace, raw_folder_id):
    folder_id = _parse_uuid(raw_folder_id or "")
    if folder_id is None:
        return None
    return MediaFolder.objects.filter(id=folder_id, workspace=workspace).first()


@require_GET
@require_permission("create_posts")
def plan(request, workspace_id):
    """步进器预览 JSON：合格视频数、各账号 7 天空槽数、默认数量。"""
    workspace = _get_workspace(request, workspace_id)
    folder = _parse_folder(workspace, request.GET.get("folder", ""))
    if folder is None:
        return JsonResponse({"error": "Choose a folder first."}, status=400)

    account_ids = _parse_selected_account_ids(request.GET.get("accounts", ""))
    data = batch_schedule.build_plan(workspace, folder, account_ids)
    data["folder"] = str(folder.id)
    data["folder_name"] = folder.name
    return JsonResponse(data)


@require_POST
@require_permission("create_posts")
def enqueue(request, workspace_id):
    """一键批量入队。成功返回 {batch_id, created}。"""
    workspace = _get_workspace(request, workspace_id)
    folder = _parse_folder(workspace, request.POST.get("folder_id", ""))
    if folder is None:
        return JsonResponse({"error": "Choose a folder first."}, status=400)

    account_ids = _parse_selected_account_ids(request.POST.get("selected_accounts", ""))
    # FB Reel 形态快照：透传 facebook_post_type_<accountId> 表单字段。
    fb_extras = {
        key: value
        for key, value in request.POST.items()
        if key.startswith("facebook_post_type_")
    }
    try:
        batch, created = batch_schedule.enqueue_batch(
            workspace=workspace,
            user=request.user,
            folder=folder,
            account_ids=account_ids,
            count=request.POST.get("count", 0),
            caption=request.POST.get("caption", ""),
            first_comment=request.POST.get("first_comment", ""),
            facebook_post_types=fb_extras,
        )
    except BatchScheduleError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    return JsonResponse(
        {
            "batch_id": str(batch.id),
            "created": created,
            "folder_name": batch.folder_name,
        }
    )


@require_GET
@require_permission("create_posts")
def active(request, workspace_id):
    """发布队列页批次条数据：仍有 scheduled 帖子的批次。"""
    workspace = _get_workspace(request, workspace_id)
    batches = batch_schedule.active_batches(workspace)
    return JsonResponse(
        [
            {
                "batch_id": str(batch.id),
                "folder_name": batch.folder_name or "Batch",
                "remaining": batch.remaining,
            }
            for batch in batches
        ],
        safe=False,
    )


@require_POST
@require_permission("create_posts")
def clear(request, workspace_id, batch_id):
    """一键清除批次内仍可删除（未发布）的帖子。"""
    workspace = _get_workspace(request, workspace_id)
    batch = get_object_or_404(
        ZhScheduledBatch, id=batch_id, workspace=workspace
    )
    cleared = batch_schedule.clear_batch(batch)
    return JsonResponse({"cleared": cleared})
