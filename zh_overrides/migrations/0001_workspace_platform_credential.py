import uuid

import django.db.models.deletion
from django.db import migrations, models

import apps.common.encryption


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("workspaces", "0003_alter_workspace_primary_color_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="WorkspacePlatformCredential",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "platform",
                    models.CharField(
                        choices=[
                            ("facebook", "Facebook"),
                            ("instagram", "Instagram"),
                            ("instagram_login", "Instagram (Direct)"),
                            ("linkedin_personal", "LinkedIn (Personal Profile)"),
                            ("linkedin_company", "LinkedIn (Company Page)"),
                            ("tiktok", "TikTok"),
                            ("youtube", "YouTube"),
                            ("pinterest", "Pinterest"),
                            ("threads", "Threads"),
                            ("bluesky", "Bluesky"),
                            ("google_business", "Google Business Profile"),
                            ("mastodon", "Mastodon"),
                            ("devto", "DEV.to"),
                        ],
                        max_length=30,
                    ),
                ),
                (
                    "credentials",
                    apps.common.encryption.EncryptedJSONField(
                        default=dict,
                        help_text="加密 JSON：工作区专属的平台应用凭证，例如 "
                        '{"client_id": "...", "client_secret": "..."}',
                    ),
                ),
                ("is_configured", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "workspace",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="workspace_platform_credentials",
                        to="workspaces.workspace",
                    ),
                ),
            ],
            options={
                "verbose_name": "工作区平台凭证",
                "verbose_name_plural": "工作区平台凭证",
                "db_table": "zh_overrides_workspace_platform_credential",
                "ordering": ["workspace__name", "platform"],
                "unique_together": {("workspace", "platform")},
            },
        ),
    ]
