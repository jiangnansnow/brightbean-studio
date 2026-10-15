"""自动候补排期管理命令：1Panel 计划任务每 10 分钟执行一次。

    python manage.py zh_auto_schedule --once

单次遍历所有启用规则，把各目标账号未来 48 小时的空槽补齐。幂等：账本保证
同一 (账号, 视频) 不重复投递，重复执行无副作用。
"""

from django.core.management.base import BaseCommand

from zh_overrides.auto_schedule import run_all_active_rules


class Command(BaseCommand):
    help = "Run zh_overrides auto-schedule rules once (48h rolling window)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            required=True,
            help="Single pass over all active rules (cron entrypoint).",
        )

    def handle(self, *args, **options):
        total = run_all_active_rules()
        self.stdout.write(
            self.style.SUCCESS(f"zh_auto_schedule: {total} post(s) queued")
        )
