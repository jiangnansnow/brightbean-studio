"""Local-custom data models (zh_hans overlay).

- ``WorkspacePlatformCredential``: per-workspace social app credentials.
- ``WorkspaceMeta``: operator-only notes for the tenant console.
- ``ZhScheduledBatch`` / ``ZhScheduledBatchItem``: 作曲器「文件夹」模式一键
  批量入队的批次与明细（本地定制功能，全部放在 zh_overrides，不触碰上游表）。

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

from django.conf import settings
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


class WorkspaceMeta(models.Model):
    """Operator-only notes for a workspace (local-custom admin console).

    Holds the Tester / platform-account ledger columns that have no
    representation upstream (tester identities, Page/IG IDs for cross-check).
    One row per workspace, created lazily by the console services.
    """

    workspace = models.OneToOneField(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="workspace_meta",
    )
    fb_tester_note = models.CharField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="FB 测试员 / Page ID 备注",
    )
    ig_tester_note = models.CharField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="IG 测试员 / IG ID 备注",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "zh_overrides_workspace_meta"
        verbose_name = "工作区运营备注"
        verbose_name_plural = "工作区运营备注"

    def __str__(self):
        return f"meta:{self.workspace.name}"


class ZhScheduledBatch(models.Model):
    """作曲器「文件夹」模式一键批量入队的一个批次。

    用户在作曲器选择单个媒体文件夹、N 个视频与勾选账号后一次性入队，服务端
    为每个视频建一条 Post，并在每个勾选账号上各占一个未来 7 天内的空闲时段。
    批次仅用于在发布队列页呈现「批次系统标签」与一键清除；不驱动任何后台
    定时任务（无持久规则、无开关）。
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="zh_scheduled_batches",
    )
    media_folder = models.ForeignKey(
        "media_library.MediaFolder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="zh_scheduled_batches",
        help_text="本次批量入队的来源文件夹（删除文件夹后批次记录保留）",
    )
    # 文件夹名快照：来源文件夹被删后，队列页批次条仍能显示名称。
    folder_name = models.CharField(max_length=255, blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="zh_scheduled_batches",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "zh_overrides_scheduled_batch"
        verbose_name = "批量排期批次"
        verbose_name_plural = "批量排期批次"
        ordering = ["-created_at"]

    def __str__(self):
        return f"批量批次:{self.folder_name or self.id}"


class ZhScheduledBatchItem(models.Model):
    """批次内一条入队帖子（一个视频对应一条 Post）。

    Post 被删除时级联清除（含一键批量清除）；已发布（历史）的 Post 不会被
    清除，对应明细保留，批次条只统计仍处于 scheduled 的帖子。
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(
        ZhScheduledBatch,
        on_delete=models.CASCADE,
        related_name="items",
    )
    post = models.ForeignKey(
        "composer.Post",
        on_delete=models.CASCADE,
        related_name="zh_batch_items",
    )
    media_asset = models.ForeignKey(
        "media_library.MediaAsset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="zh_batch_items",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "zh_overrides_scheduled_batch_item"
        verbose_name = "批量排期明细"
        verbose_name_plural = "批量排期明细"
        unique_together = [("batch", "post")]
        indexes = [models.Index(fields=["batch", "post"])]

    def __str__(self):
        return f"批次明细:{self.batch_id}:{self.post_id}"
