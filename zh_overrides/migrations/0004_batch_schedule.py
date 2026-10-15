import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('composer', '0022_platformpost_analytics_column_defaults'),
        ('media_library', '0003_pendingupload'),
        ('workspaces', '0003_alter_workspace_primary_color_and_more'),
        ('zh_overrides', '0003_backfill_verified_emailaddress'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ZhScheduledBatch',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('folder_name', models.CharField(blank=True, default='', max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='zh_scheduled_batches', to=settings.AUTH_USER_MODEL)),
                ('media_folder', models.ForeignKey(blank=True, help_text='本次批量入队的来源文件夹（删除文件夹后批次记录保留）', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='zh_scheduled_batches', to='media_library.mediafolder')),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='zh_scheduled_batches', to='workspaces.workspace')),
            ],
            options={
                'verbose_name': '批量排期批次',
                'verbose_name_plural': '批量排期批次',
                'db_table': 'zh_overrides_scheduled_batch',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ZhScheduledBatchItem',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('batch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='zh_overrides.zhscheduledbatch')),
                ('media_asset', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='zh_batch_items', to='media_library.mediaasset')),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='zh_batch_items', to='composer.post')),
            ],
            options={
                'verbose_name': '批量排期明细',
                'verbose_name_plural': '批量排期明细',
                'db_table': 'zh_overrides_scheduled_batch_item',
                'indexes': [models.Index(fields=['batch', 'post'], name='zh_override_batch_i_2e7977_idx')],
                'unique_together': {('batch', 'post')},
            },
        ),
    ]
