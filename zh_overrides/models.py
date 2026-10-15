"""Local-custom data models (zh_hans overlay).

- ``WorkspacePlatformCredential``: per-workspace social app credentials.
- ``WorkspaceMeta``: operator-only notes for the tenant console.
- ``ZhAutoScheduleRule`` / ``ZhAutoScheduleConsumption``: 文件夹自动候补排期
  规则与消耗账本（48 小时滚动窗口、10 分钟后台扫描、社交页总开关）。
- ``ZhScheduledBatch`` / ``ZhScheduledBatchItem``: 自动候补每次投递的批次与明细
  （发布队列页「自动」标签与一键清除）。

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


class ZhAutoScheduleRule(models.Model):
    """文件夹自动候补排期规则（每工作区至多一条）。

    用户在帖子编辑器勾选平台账号并选定监听文件夹后「开启自动候补」：系统每
    10 分钟扫描一次，使每个目标账号未来 48 小时内的空槽始终排满该文件夹内
    FIFO 最前的合格视频。文案/首评/Facebook 形态在开启瞬间快照入规则。
    社交账号页总开关只负责停用/原样恢复，不承载任何配置。
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.OneToOneField(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="zh_auto_schedule_rule",
    )
    media_folder = models.ForeignKey(
        "media_library.MediaFolder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="zh_auto_schedule_rules",
        help_text="监听的媒体文件夹；null 表示监听未分文件夹的根目录散素材；来源被删后置空",
    )
    # 文件夹名快照：空串=根目录；非空但 media_folder 为空=原文件夹已被删除。
    folder_name = models.CharField(max_length=255, blank=True, default="")
    accounts = models.ManyToManyField(
        "social_accounts.SocialAccount",
        related_name="zh_auto_schedule_rules",
        help_text="参与自动候补的目标账号",
    )
    caption = models.TextField(blank=True, default="", verbose_name="文案快照")
    first_comment = models.TextField(blank=True, default="", verbose_name="首评快照")
    facebook_post_type = models.CharField(
        max_length=10,
        blank=True,
        default="",
        choices=[("", "普通视频"), ("reel", "Reel")],
        verbose_name="Facebook 视频形态快照",
        help_text="单账号粒度以 facebook_post_types JSON 为准，此字段为历史兼容",
    )
    facebook_post_types = models.JSONField(
        default=dict,
        blank=True,
        help_text='各 FB 账号形态快照，形如 {"<account_id>": "reel"}',
    )
    is_active = models.BooleanField(default=False, verbose_name="是否启用")
    enabled_at = models.DateTimeField(null=True, blank=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "zh_overrides_auto_schedule_rule"
        verbose_name = "自动候补排期规则"
        verbose_name_plural = "自动候补排期规则"

    def __str__(self):
        state = "启用" if self.is_active else "停用"
        label = self.folder_name or "媒体库根目录"
        return f"自动候补[{state}]:{self.workspace_id}->{label}"

    @property
    def folder_missing(self):
        """监听的命名文件夹已被用户删除（根目录规则不受影响）。"""
        return bool(self.folder_name) and self.media_folder_id is None


class ZhAutoScheduleConsumption(models.Model):
    """自动候补消耗账本：(账号, 视频) 已成功投递记录。

    纯内部数据，前台不展示。记账发生在成功入队的同一事务内：发布失败、手动
    取消、一键清除、停用/恢复、整单替换都不触发二次投递；唯一约束从数据库层
    杜绝同账号重复建帖。
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rule = models.ForeignKey(
        ZhAutoScheduleRule,
        on_delete=models.CASCADE,
        related_name="consumptions",
    )
    social_account = models.ForeignKey(
        "social_accounts.SocialAccount",
        on_delete=models.CASCADE,
        related_name="zh_auto_consumptions",
    )
    media_asset = models.ForeignKey(
        "media_library.MediaAsset",
        on_delete=models.CASCADE,
        related_name="zh_auto_consumptions",
    )
    post = models.ForeignKey(
        "composer.Post",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="zh_auto_consumptions",
    )
    platform_post = models.ForeignKey(
        "composer.PlatformPost",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="zh_auto_consumptions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "zh_overrides_auto_schedule_consumption"
        verbose_name = "自动候补消耗记录"
        verbose_name_plural = "自动候补消耗记录"
        unique_together = [("social_account", "media_asset")]
        indexes = [models.Index(fields=["rule", "social_account"])]

    def __str__(self):
        return f"消耗:{self.social_account_id}:{self.media_asset_id}"


class ZhScheduledBatch(models.Model):
    """自动候补（或一键批量）每次投递生成的一个批次。

    每次后台扫描实际投递 N 个视频即产生一个批次，用于在发布队列页呈现
    「自动」系统标签与一键清除；批次本身不驱动投递。
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="zh_scheduled_batches",
    )
    rule = models.ForeignKey(
        ZhAutoScheduleRule,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="batches",
    )
    media_folder = models.ForeignKey(
        "media_library.MediaFolder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="zh_scheduled_batches",
        help_text="本次投递的来源文件夹（删除文件夹后批次记录保留）",
    )
    # 文件夹名快照：来源文件夹被删后，队列页标签仍能显示；空串=根目录。
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
