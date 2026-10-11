from django.contrib import admin

from .forms import WorkspacePlatformCredentialAdminForm
from .models import WorkspacePlatformCredential


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
