"""文件夹自动候补排期视图层（zh_overrides 本地定制）。

端点挂在工作区前缀下，复用上游作曲器的工作区成员校验
（``apps.composer.views._get_workspace``）与成员权限装饰器，不复制鉴权逻辑。
文件夹浏览走 htmx 片段；开启/停用/状态/批次操作均返回 JSON。
"""

from __future__ import annotations

import uuid

from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.composer.views import _get_workspace, _parse_selected_account_ids
from apps.media_library.models import MediaFolder
from apps.members.decorators import require_permission

from . import auto_schedule
from .auto_schedule import AutoScheduleError
from .models import ZhAutoScheduleRule, ZhScheduledBatch

_TEMPLATE_DIR = "zh_overrides/auto_schedule/"

# 前端根目录卡片使用的文件夹 id 占位。
ROOT_FOLDER_ID = "root"


def _folder_chain(folder):
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
    """文件夹浏览片段：根级（含「未分文件夹」根目录卡片）或指定父文件夹。"""
    workspace = _get_workspace(request, workspace_id)
    parent = None
    raw_parent = request.GET.get("parent", "").strip()
    if raw_parent and raw_parent != ROOT_FOLDER_ID:
        parent = get_object_or_404(MediaFolder, id=raw_parent, workspace=workspace)

    sub_folders = list(
        MediaFolder.objects.filter(workspace=workspace, parent_folder=parent)
        .annotate(sub_count=Count("subfolders", distinct=True))
        .order_by("name")
    )
    video_counts = auto_schedule.folder_video_counts(workspace, sub_folders)
    for folder in sub_folders:
        folder.zh_video_count = video_counts.get(folder.id, 0)
    root_count = auto_schedule.root_video_count(workspace) if parent is None else 0

    rule = ZhAutoScheduleRule.objects.filter(workspace=workspace).first()
    selected_id = ROOT_FOLDER_ID if rule and rule.media_folder_id is None else (
        str(rule.media_folder_id) if rule and rule.media_folder_id else ""
    )

    return render(
        request,
        _TEMPLATE_DIR + "_folder_grid.html",
        {
            "workspace": workspace,
            "folders": sub_folders,
            "parent": parent,
            "chain": _folder_chain(parent) if parent else [],
            "root_count": root_count,
            "root_id": ROOT_FOLDER_ID,
            "selected_id": selected_id,
        },
    )


@require_GET
@require_permission("create_posts")
def panel(request, workspace_id):
    """规则运行状态 JSON：是否启用、监听标签、已投递数、跳过账号。"""
    workspace = _get_workspace(request, workspace_id)
    rule = ZhAutoScheduleRule.objects.filter(workspace=workspace).first()
    if rule is None:
        return JsonResponse({"has_rule": False, "can_enable": True})
    status = auto_schedule.rule_status(rule)
    status["has_rule"] = True
    return JsonResponse(status)


def _snapshot_from_post(request):
    """从作曲器表单提取开启瞬间的文案/首评/FB 形态快照。"""
    return {
        "caption": request.POST.get("caption", ""),
        "first_comment": request.POST.get("first_comment", ""),
        **{
            key: value
            for key, value in request.POST.items()
            if key.startswith("facebook_post_type_")
        },
    }


@require_POST
@require_permission("create_posts")
def enable(request, workspace_id):
    """开启自动候补或整单替换监听目标。成功立即补排一次。"""
    workspace = _get_workspace(request, workspace_id)
    raw_folder = request.POST.get("folder_id", "").strip()
    if raw_folder == ROOT_FOLDER_ID:
        folder = None  # 监听未分文件夹的根目录散素材
    else:
        folder_id = _parse_uuid(raw_folder)
        if folder_id is None:
            return JsonResponse(
                {"error": "Choose a folder first."}, status=400
            )
        folder = MediaFolder.objects.filter(id=folder_id, workspace=workspace).first()
        if folder is None:
            return JsonResponse(
                {"error": "Choose a folder first."}, status=400
            )

    account_ids = _parse_selected_account_ids(request.POST.get("selected_accounts", ""))
    try:
        rule, created = auto_schedule.enable_rule(
            workspace=workspace,
            user=request.user,
            folder=folder,
            account_ids=account_ids,
            form_snapshot=_snapshot_from_post(request),
        )
    except AutoScheduleError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    return JsonResponse({"enabled": True, "queued_now": created, **auto_schedule.rule_status(rule)})


@require_POST
@require_permission("create_posts")
def disable(request, workspace_id):
    """作曲器弹窗内停用（社交页总开关走 toggle）。已在队列的帖子不动。"""
    workspace = _get_workspace(request, workspace_id)
    rule = get_object_or_404(ZhAutoScheduleRule, workspace=workspace)
    rule.is_active = False
    rule.save(update_fields=["is_active", "updated_at"])
    return JsonResponse({"enabled": False, **auto_schedule.rule_status(rule)})


@require_GET
@require_permission("create_posts")
def social_toggle_state(request, workspace_id):
    """社交账号页总开关初始状态。"""
    return panel(request, workspace_id)


@require_POST
@require_permission("create_posts")
def social_toggle(request, workspace_id):
    """社交页总开关：启用⇄停用。

    - 无规则：前端禁用不可提交（无文件夹/账号可恢复）；
    - 规则存在但监听文件夹被删：不允许直接恢复，提示回编辑器重选；
    - 由停用转启用＝原样恢复，立即补排一次。
    """
    workspace = _get_workspace(request, workspace_id)
    rule = ZhAutoScheduleRule.objects.filter(workspace=workspace).first()
    if rule is None:
        return JsonResponse(
            {"error": "Enable this in the post composer first."}, status=400
        )

    if rule.is_active:
        rule.is_active = False
        rule.save(update_fields=["is_active", "updated_at"])
        return JsonResponse({"enabled": False, **auto_schedule.rule_status(rule)})

    if rule.folder_missing:
        return JsonResponse(
            {"error": "Folder no longer exists; re-select it in the composer."},
            status=400,
        )

    rule.is_active = True
    rule.enabled_at = timezone.now()
    rule.save(update_fields=["is_active", "enabled_at", "updated_at"])
    try:
        queued = auto_schedule.run_rule(rule)
    except AutoScheduleError as exc:
        rule.is_active = False
        rule.save(update_fields=["is_active", "updated_at"])
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse({"enabled": True, "queued_now": queued, **auto_schedule.rule_status(rule)})


@require_GET
@require_permission("create_posts")
def active(request, workspace_id):
    """发布队列页「自动」批次标签数据。"""
    workspace = _get_workspace(request, workspace_id)
    return JsonResponse(
        [
            {
                "batch_id": str(batch.id),
                "remaining": batch.remaining,
            }
            for batch in auto_schedule.active_batches(workspace)
        ],
        safe=False,
    )


@require_POST
@require_permission("create_posts")
def clear(request, workspace_id, batch_id):
    """一键清除批次内仍可删除（未发布）的帖子。"""
    workspace = _get_workspace(request, workspace_id)
    batch = get_object_or_404(ZhScheduledBatch, id=batch_id, workspace=workspace)
    cleared = auto_schedule.clear_batch(batch)
    return JsonResponse({"cleared": cleared})
