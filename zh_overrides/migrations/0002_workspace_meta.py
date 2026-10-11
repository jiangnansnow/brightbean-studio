import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("zh_overrides", "0001_workspace_platform_credential"),
    ]

    operations = [
        migrations.CreateModel(
            name="WorkspaceMeta",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "fb_tester_note",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=500,
                        verbose_name="FB 测试员 / Page ID 备注",
                    ),
                ),
                (
                    "ig_tester_note",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=500,
                        verbose_name="IG 测试员 / IG ID 备注",
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "workspace",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="workspace_meta",
                        to="workspaces.workspace",
                    ),
                ),
            ],
            options={
                "verbose_name": "工作区运营备注",
                "verbose_name_plural": "工作区运营备注",
                "db_table": "zh_overrides_workspace_meta",
            },
        ),
    ]
