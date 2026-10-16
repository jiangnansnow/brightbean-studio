"""View or clear runtime leak captures.

Usage:
    python manage.py zhleak            # list unique untranslated texts
    python manage.py zhleak --clear    # delete the collected file
"""

import json

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "List untranslated strings collected by the runtime leak collector."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete the collected leaks file.",
        )

    def handle(self, *args, **options):
        from zh_overrides import leak_collector

        d = leak_collector._collect_dir()
        f = d / "leaks.jsonl"

        if options["clear"]:
            if f.exists():
                f.unlink()
                self.stdout.write(self.style.SUCCESS(f"已清空 {f}"))
            else:
                self.stdout.write("未找到漏翻文件，无需清理。")
            return

        if not f.exists() or f.stat().st_size == 0:
            self.stdout.write("尚未收集到漏翻（收集开关关闭，或还没有命中未翻译文本）。")
            return

        seen: dict[str, int] = {}
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                text = json.loads(line)["text"]
            except Exception:
                continue
            seen[text] = seen.get(text, 0) + 1

        for text in sorted(seen):
            self.stdout.write(text)
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"共 {len(seen)} 条唯一漏翻文本。"))