"""Admin console: superuser-only tenant configuration matrix.

Mounted as a custom admin site page (no upstream edits):
    /admin/zh_overrides/tenant-config/
"""

from __future__ import annotations

from django.contrib import admin, messages
from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import escape
from django.views.decorators.http import require_http_methods

from . import admin_console_services as svc


def _superuser_required(view_func):
    def wrapped(request, *args, **kwargs):
        if not request.user.is_active or not request.user.is_superuser:
            return HttpResponseForbidden("仅超级管理员可访问租户配置控制台。")
        return view_func(request, *args, **kwargs)

    wrapped.__name__ = view_func.__name__
    return staff_member_required(wrapped)


def _log(request, obj, action_flag, message: str):
    LogEntry.objects.log_action(
        user_id=request.user.pk,
        content_type_id=ContentType.objects.get_for_model(obj).pk,
        object_id=str(obj.pk),
        object_repr=str(obj)[:200],
        action_flag=action_flag,
        change_message=message,
    )


def _bundles_from_post(prefix: str, post) -> dict[str, svc.OrgBundle]:
    def val(key):
        return (post.get(key) or "").strip()

    return {
        svc.FB: svc.OrgBundle(
            client_id=val(f"{prefix}_fb_id"),
            client_secret=val(f"{prefix}_fb_secret"),
        ),
        svc.IG: svc.OrgBundle(
            client_id=val(f"{prefix}_ig_id"),
            client_secret=val(f"{prefix}_ig_secret"),
        ),
    }


@_superuser_required
@require_http_methods(["GET"])
def tenant_config_view(request):
    tenants = svc.load_tenants()
    admins = [
        {"email": u.email, "name": u.name or u.email, "last_login": u.last_login}
        for u in svc.User.objects.filter(is_superuser=True, is_active=True).order_by("email")
    ]
    stats = {
        "orgs": svc.Organization.objects.count(),
        "workspaces": svc.Workspace.objects.count(),
        "accounts": svc.SocialAccount.objects.filter(platform__in=svc.PLATFORMS).count(),
        "admins": len(admins),
    }
    context = {
        **admin.site.each_context(request),
        "title": "租户配置矩阵",
        "tenants": tenants,
        "admins": admins,
        "stats": stats,
        "fb": svc.FB,
        "ig": svc.IG,
        "opts": {"app_label": "zh_overrides"},  # admin template breadcrumbs
    }
    return render(request, "zh_overrides/admin/tenant_config.html", context)


@_superuser_required
@require_http_methods(["POST"])
def tenant_config_action(request):
    action = request.POST.get("action", "")
    org_id = request.POST.get("organization_id", "")
    try:
        if action == "create_tenant":
            org = svc.create_tenant(
                email=request.POST.get("email", ""),
                password=request.POST.get("password", ""),
                organization_name=request.POST.get("organization_name", ""),
            )
            _log(request, org, ADDITION, f"租户配置控制台：创建租户账号与组织「{org.name}」")
            messages.success(request, f"租户「{org.name}」已创建（含默认工作区）。")

        elif action == "save_mode":
            mode = request.POST.get("mode", "")
            bundles = _bundles_from_post("org", request.POST)
            svc.save_tenant_mode(
                org_id, mode, bundles,
                organization_name=request.POST.get("organization_name", ""),
            )
            org = svc.Organization.objects.get(id=org_id)
            _log(request, org, CHANGE, f"租户配置控制台：切换/保存模式为 {mode}")
            messages.success(request, f"租户「{org.name}」已保存为{'通用' if mode == 'traditional' else '独立'}模式。")
            if request.POST.get("test") == "1" and mode == "traditional":
                for platform in (svc.FB, svc.IG):
                    ok, detail = svc.probe_credential(platform, bundles[platform])
                    (messages.success if ok else messages.error)(
                        request, f"[凭证测试·{svc.PLATFORM_LABELS[platform]}] {detail}"
                    )

        elif action == "upsert_workspace":
            ws_id = request.POST.get("workspace_id") or None
            bundles = _bundles_from_post("ws", request.POST)
            ws = svc.upsert_workspace(
                organization_id=org_id,
                name=request.POST.get("workspace_name", ""),
                workspace_id=ws_id,
                credentials=bundles,
                notes={
                    svc.FB: request.POST.get("fb_note", ""),
                    svc.IG: request.POST.get("ig_note", ""),
                },
            )
            _log(request, ws, ADDITION if ws_id is None else CHANGE, "租户配置控制台：保存工作区及凭证/备注")
            messages.success(request, f"工作区「{ws.name}」已保存。")
            if request.POST.get("test") == "1":
                for platform in (svc.FB, svc.IG):
                    b = bundles[platform]
                    if not (b.client_id.strip() and b.client_secret.strip()):
                        messages.warning(
                            request,
                            f"[凭证测试·{svc.PLATFORM_LABELS[platform]}] 该平台未填写完整，已跳过测试（空配置=不可连接）。",
                        )
                        continue
                    ok, detail = svc.probe_credential(platform, b)
                    (messages.success if ok else messages.error)(
                        request, f"[凭证测试·{svc.PLATFORM_LABELS[platform]}] {detail}"
                    )

        elif action == "archive_workspace":
            svc.archive_workspace(org_id, request.POST.get("workspace_id", ""))
            ws = svc.Workspace.objects.get(id=request.POST["workspace_id"])
            _log(request, ws, CHANGE, "租户配置控制台：归档工作区（可逆）")
            messages.success(request, f"工作区「{ws.name}」已归档。")

        elif action == "unarchive_workspace":
            svc.unarchive_workspace(org_id, request.POST.get("workspace_id", ""))
            ws = svc.Workspace.objects.get(id=request.POST["workspace_id"])
            _log(request, ws, CHANGE, "租户配置控制台：取消归档工作区")
            messages.success(request, f"工作区「{ws.name}」已恢复。")

        elif action == "delete_org":
            org = svc.Organization.objects.filter(id=org_id).first()
            name = org.name if org else org_id
            ws_count = svc.delete_organization(org_id)
            if org:
                _log(request, org, DELETION, f"租户配置控制台：彻底删除组织（级联 {ws_count} 个工作区及全部数据）")
            messages.warning(request, f"组织「{name}」及其 {ws_count} 个工作区已彻底删除。")
            return _redirect_to_console(org_id=None)

        elif action == "delete_workspace":
            ws = svc.Workspace.objects.filter(
                id=request.POST.get("workspace_id", ""), organization_id=org_id
            ).first()
            name = ws.name if ws else request.POST.get("workspace_id", "")
            svc.delete_workspace(org_id, request.POST.get("workspace_id", ""))
            if ws:
                _log(request, ws, DELETION, "租户配置控制台：彻底删除工作区（级联删除帖子/账号/凭证）")
            messages.warning(request, f"工作区「{name}」已彻底删除。")
        else:
            messages.error(request, f"未知操作：{escape(action)}")
    except svc.ConsoleError as exc:
        messages.error(request, str(exc))
    except Exception:  # pragma: no cover - defensive surface
        import logging

        logging.getLogger("zh_overrides").exception("tenant console action failed")
        messages.error(request, "保存失败，请检查输入后重试（详见服务器日志）。")

    ws_anchor = request.POST.get("workspace_id") or None
    if action in {"delete_workspace"}:
        ws_anchor = None
    return _redirect_to_console(org_id=org_id, ws_anchor=ws_anchor)


def _redirect_to_console(org_id: str | None = None, ws_anchor: str | None = None):
    from django.shortcuts import redirect

    url = reverse("admin:zh_overrides_tenant_config")
    if ws_anchor:
        url += f"#ws-{ws_anchor}"
    elif org_id:
        url += f"#org-{org_id}"
    return redirect(url)
