"""Workspace-scoped platform app credentials (local-custom feature).

Why a sidecar table instead of touching upstream ``PlatformCredential``:

* Upstream credentials are keyed ``(organization, platform)`` — one app per
  platform per org, shared by every workspace. Operators running agency-style
  deployments may need each workspace to talk to its *own* Meta/Google/etc.
  developer app (separate quota pools, separate review/risk, test-app builds).
* This model adds the ``(workspace, platform)`` key without altering any
  upstream table, migration, admin or form, so rebasing onto upstream/main
  never conflicts on the storage layer.

Resolution rules (implemented in
``apps.credentials.models.resolve_platform_credentials``):

1. A complete env config wins globally (unchanged upstream behaviour).
2. Else a complete **org** row wins — "traditional mode": the whole org
   shares one app and workspace rows are ignored.
3. Else the **workspace** row is used — "independent mode": a workspace
   without its own row is simply unconfigured (no fallback to a default).
"""

import uuid

from django.db import models

from apps.common.encryption import EncryptedJSONField
from apps.credentials.models import (
    PlatformCredential,
    derive_is_configured,
)


class WorkspacePlatformCredential(models.Model):
    """App credentials (App ID / App Secret) bound to a single workspace."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="workspace_platform_credentials",
    )
    platform = models.CharField(max_length=30, choices=PlatformCredential.Platform.choices)
    credentials = EncryptedJSONField(
        default=dict,
        help_text="加密 JSON：工作区专属的平台应用凭证，例如 "
        '{"client_id": "...", "client_secret": "..."}',
    )
    is_configured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "zh_overrides_workspace_platform_credential"
        verbose_name = "工作区平台凭证"
        verbose_name_plural = "工作区平台凭证"
        unique_together = [("workspace", "platform")]
        ordering = ["workspace__name", "platform"]

    def __str__(self):
        return f"{self.workspace.name} - {self.get_platform_display()}"

    def save(self, *args, **kwargs):
        # Same derived-gate contract as the upstream PlatformCredential:
        # a row is active only when it carries every key its provider needs.
        self.is_configured = derive_is_configured(self.platform, self.credentials)
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            kwargs["update_fields"] = {*update_fields, "is_configured"}
        super().save(*args, **kwargs)

    @property
    def masked_credentials(self):
        """Credentials with secrets masked (last 4 chars only)."""
        masked = {}
        for key, value in (self.credentials or {}).items():
            if isinstance(value, str) and len(value) > 4:
                masked[key] = "****" + value[-4:]
            else:
                masked[key] = "****"
        return masked
