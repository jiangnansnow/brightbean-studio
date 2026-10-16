from django.contrib import admin
from django.urls import path

from . import admin_console
from .forms import WorkspacePlatformCredentialAdminForm
from .models import (
    WorkspaceMeta,
    WorkspacePlatformCredential,
    ZhAutoScheduleConsumption,
    ZhAutoScheduleRule,
)


@admin.register(WorkspacePlatformCredential)
class WorkspacePlatformCredentialAdmin(admin.ModelAdmin):
    form = WorkspacePlatformCredentialAdminForm
    list_display = ("workspace", "platform", "is_configured", "updated_at")
    list_filter = ("platform", "is_configured")
    search_fields = ("workspace__name", "workspace__organization__name")
    readonly_fields = ("id", "is_configured", "created_at", "updated_at")

    # Same hard gate as the upstream PlatformCredential admin: editing
    # credentials reveals decrypted secrets on the change page.
    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "tenant-config/",
                self.admin_site.admin_view(admin_console.tenant_config_view),
                name="zh_overrides_tenant_config",
            ),
            path(
                "tenant-config/action/",
                self.admin_site.admin_view(admin_console.tenant_config_action),
                name="zh_overrides_tenant_config_action",
            ),
        ]
        return custom + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["console_url"] = "/admin/zh_overrides/workspaceplatformcredential/tenant-config/"
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(WorkspaceMeta)
class WorkspaceMetaAdmin(admin.ModelAdmin):
    list_display = ("workspace", "updated_at")
    search_fields = ("workspace__name",)
    readonly_fields = ("updated_at",)

    def has_module_permission(self, request):
        # Edited via the tenant console; hidden from the main admin menu.
        return False


# 规则/账本/批次只服务前台自动候补逻辑，刻意不注册 Admin（用户明确：前台功能
# 不进后台菜单）。保留 import 是为了让模型在 admin autodiscover 时正常装载。
_ = (ZhAutoScheduleRule, ZhAutoScheduleConsumption)
