"""Detect drift between zh_overrides template copies and upstream templates.

Run after every `git rebase main` (upstream sync):

    python manage.py zhcheck

For each override file, the Django template tag/variable token multiset is
compared with its upstream counterpart. Translation must only change human
language, never template logic, so any token difference means the copy needs
re-syncing. Also flags overrides whose upstream file was deleted.

Exit code is non-zero when drift is found, so it can gate automation.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

_TAG_RE = re.compile(r"{%\s*(.*?)\s*%}", re.DOTALL)
_VAR_RE = re.compile(r"{{\s*(.*?)\s*}}", re.DOTALL)


def _tokens(source: str) -> Counter:
    return Counter(_TAG_RE.findall(source) + _VAR_RE.findall(source))


class Command(BaseCommand):
    help = "Check zh_overrides templates for drift against upstream templates."

    def handle(self, *args, **options):
        base_dir = Path(settings.BASE_DIR)
        zh_dir = base_dir / "zh_overrides" / "templates"
        upstream_dir = base_dir / "templates"
        allow_path = base_dir / "zh_overrides" / "drift-allowlist.json"
        allowlist = {}
        if allow_path.exists():
            allowlist = json.loads(allow_path.read_text(encoding="utf-8"))
        # 有意新增的纯中文模板（如法律页），无上游对应文件，不做漂移比对。
        added_ok = set(allowlist.get("_added", []))

        if not zh_dir.exists():
            self.stdout.write(self.style.WARNING("No zh_overrides/templates directory; nothing to check."))
            return

        checked = 0
        problems = 0

        for override in sorted(zh_dir.rglob("*.html")):
            rel = override.relative_to(zh_dir)
            rel_key = rel.as_posix()
            upstream = upstream_dir / rel
            checked += 1

            if not upstream.exists():
                if rel_key in added_ok:
                    self.stdout.write(self.style.SUCCESS(f"[OK-ADDED] {rel} (intentional new template)"))
                    continue
                problems += 1
                self.stdout.write(self.style.ERROR(f"[DELETED UPSTREAM] {rel}"))
                self.stdout.write("    Upstream template removed; delete or relocate this override.")
                continue

            zh_tokens = _tokens(override.read_text(encoding="utf-8"))
            en_tokens = _tokens(upstream.read_text(encoding="utf-8"))

            allowed = allowlist.get(rel_key, {})

            def _normalize(items):
                # Accept either bare token content or {{ }}/{% %} wrapped form.
                result = []
                for item in items:
                    item = item.strip()
                    if item.startswith(("{{", "{%")) and item.endswith(("}}", "%}")):
                        item = item[2:-2].strip()
                    result.append(item)
                return Counter(result)

            allowed_missing = _normalize(allowed.get("missing", []))
            allowed_extra = _normalize(allowed.get("extra", []))

            raw_missing = en_tokens - zh_tokens  # upstream logic lost in zh copy
            raw_extra = zh_tokens - en_tokens  # logic added in zh copy
            missing = raw_missing - allowed_missing
            extra = raw_extra - allowed_extra

            # Allowed deviations that no longer occur: upstream/override moved.
            stale_missing = allowed_missing - raw_missing
            stale_extra = allowed_extra - raw_extra

            if missing or extra:
                problems += 1
                self.stdout.write(self.style.ERROR(f"[DRIFT] {rel}"))
                for token in sorted(missing):
                    self.stdout.write(f"    - missing: {{{{{token}}}}}")
                for token in sorted(extra):
                    self.stdout.write(f"    + extra:   {{{{{token}}}}}")
            elif stale_missing or stale_extra:
                problems += 1
                self.stdout.write(self.style.WARNING(f"[ALLOWLIST STALE] {rel}"))
                for token in sorted(stale_missing):
                    self.stdout.write(f"    ~ allowed but no longer missing: {{{{{token}}}}}")
                for token in sorted(stale_extra):
                    self.stdout.write(f"    ~ allowed but no longer extra: {{{{{token}}}}}")
            else:
                self.stdout.write(self.style.SUCCESS(f"[OK] {rel}"))

        self.stdout.write("")
        summary = f"Checked {checked} override file(s); {problems} problem(s)."
        if problems:
            self.stdout.write(self.style.ERROR(summary))
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS(summary))
