"""文件夹自动排期视图层（zh_overrides 本地定制，V2）。

端点挂在工作区前缀下，复用上游作曲器的工作区成员校验
（``apps.composer.views._get_workspace``）与成员权限装饰器，不复制鉴权逻辑。
文件夹浏览走 htmx 片段；队列提交/武装开关/批次操作返回 JSON。
"""

from __future__ import annotations

import uuid

from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
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
    """作曲器状态 JSON：武装开关 + 已有规则状态（决定按钮灰态与会话恢复提示）。"""
    workspace = _get_workspace(request, workspace_id)
    armed = auto_schedule.is_armed(workspace)
    rule = ZhAutoScheduleRule.objects.filter(workspace=workspace).first()
    status = {"armed": armed, "has_rule": rule is not None}
    if rule is not None:
        status.update(auto_schedule.rule_status(rule))
    return JsonResponse(status)


def _snapshot_from_post(request):
    """从作曲器表单提取提交瞬间的文案/首评/FB 形态快照。"""
    return {
        "caption": request.POST.get("caption", ""),
        "first_comment": request.POST.get("first_comment", ""),
        **{
            key: value
            for key, value in request.POST.items()
            if key.startswith("facebook_post_type_")
        },
    }


def _resolve_folder(request, workspace):
    """解析 POST 里的 folder_id 为 MediaFolder 实例（root → None）。"""
    raw_folder = request.POST.get("folder_id", "").strip()
    if raw_folder == ROOT_FOLDER_ID:
        return None  # 监听未分文件夹的根目录散素材
    folder_id = _parse_uuid(raw_folder)
    if folder_id is None:
        return None
    return MediaFolder.objects.filter(id=folder_id, workspace=workspace).first()


@require_POST
@require_permission("create_posts")
def queue(request, workspace_id):
    """作曲器文件夹模式「加入队列」提交入口（拦截原生提交）。

    校验武装开关 → 创建/更新规则 → 立即补满 24h → 返回跳转 URL（前端跳日历）。
    """
    workspace = _get_workspace(request, workspace_id)
    if not auto_schedule.is_armed(workspace):
        return JsonResponse(
            {"error": "Enable auto-schedule in workspace settings first."}, status=400
        )

    folder = _resolve_folder(request, workspace)
    if folder is None and request.POST.get("folder_id", "").strip() != ROOT_FOLDER_ID:
        return JsonResponse({"error": "Choose a folder first."}, status=400)

    account_ids = _parse_selected_account_ids(request.POST.get("selected_accounts", ""))
    try:
        rule, queued = auto_schedule.submit_folder_schedule(
            workspace=workspace,
            user=request.user,
            folder=folder,
            account_ids=account_ids,
            form_snapshot=_snapshot_from_post(request),
        )
    except AutoScheduleError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    payload = {
        "queued_now": queued,
        "redirect": reverse("calendar:calendar", kwargs={"workspace_id": workspace.id}),
        **auto_schedule.rule_status(rule),
    }
    if queued == 0:
        payload["reason"] = auto_schedule.explain_zero(rule)
    return JsonResponse(payload)


@require_GET
@require_permission("create_posts")
def social_toggle_state(request, workspace_id):
    """社交账号页总开关初始状态。"""
    workspace = _get_workspace(request, workspace_id)
    return JsonResponse({"armed": auto_schedule.is_armed(workspace)})


@require_POST
@require_permission("create_posts")
def social_toggle(request, workspace_id):
    """社交页「自动排期」总开关翻转（纯武装开关）。

    开 = 武装（不自动排期、不恢复）；关 = 停止补货且不自动恢复。
    已在队列里的帖子、账本一律不动。
    """
    workspace = _get_workspace(request, workspace_id)
    armed = auto_schedule.set_armed(workspace, not auto_schedule.is_armed(workspace))
    return JsonResponse({"armed": armed})


@require_POST
@require_permission("create_posts")
def clear_media(request, workspace_id):
    """文件夹模式激活时清空作曲器「待提交」素材（session 级，不删文件）。

    与上游 remove_pending_media 的关键区别：后者会 delete_asset 删除素材文件，
    这里仅从 session 撤销"已选中"，素材文件与媒体库记录完整保留。
    """
    workspace = _get_workspace(request, workspace_id)
    request.session.pop(f"pending_media_{workspace.id}", None)
    return JsonResponse({"ok": True})


@require_GET
@require_permission("create_posts")
def active(request, workspace_id):
    """发布队列页「自动」批次标签数据。"""
    workspace = _get_workspace(request, workspace_id)
    return JsonResponse(
        [
            {"batch_id": str(batch.id), "remaining": batch.remaining}
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
