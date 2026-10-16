"""Report the impact of a zh.json change before deployment.

Diff the current ``zh.json`` against a previous version (the last committed /
deployed copy) and, for every added / removed / changed key, show where the
English source string occurs in the templates that the overlay actually
translates. This is the deployment pre-review list: verify each listed change
is intentional and that the affected lines still make sense in Chinese.

Usage:
    python manage.py zh_diff --baseline zh_overrides/zh.json.previous
    python manage.py zh_diff --baseline zh_overrides/zh.json.previous --output 变更影响报告.txt

The baseline is an explicit file path (not ``git``): this host has no git CLI
and commits are made through the GitHub REST API, so a plain file diff keeps the
command dependency-free and deterministic.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

_DICT_PATH = Path(__file__).resolve().parents[2] / "zh.json"
_SECTIONS = ("phrases", "words", "tokens")

_LEGAL_NAMES = {"legal.html", "data_deletion.html"}
_EMAIL_PART = "/email/"
_OCCURRENCE_CAP = 25


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _roots() -> list[Path]:
    base = Path(settings.BASE_DIR)
    return [base / "templates", base / "zh_overrides" / "templates"]


def _is_skipped(rel: str) -> bool:
    return _EMAIL_PART in rel or Path(rel).name in _LEGAL_NAMES


def _occurrences(key: str) -> list[str]:
    hits: list[str] = []
    total = 0
    for root in _roots():
        if not root.exists():
            continue
        for template in sorted(root.rglob("*.html")):
            rel = template.relative_to(root).as_posix()
            if _is_skipped(rel):
                continue
            for lineno, line in enumerate(
                template.read_text(encoding="utf-8", errors="replace").splitlines(), 1
            ):
                if key in line:
                    total += 1
                    if len(hits) < _OCCURRENCE_CAP:
                        hits.append(f"        {rel}:{lineno}  {line.strip()[:120]}")
    return hits, total


def _diff_section(old: dict, new: dict) -> tuple[dict, dict, dict]:
    added = {k: new[k] for k in new if k not in old}
    removed = {k: old[k] for k in old if k not in new}
    changed = {k: (old[k], new[k]) for k in old if k in new and old[k] != new[k]}
    return added, removed, changed


def build_report(baseline_path: Path) -> str:
    current = _load(_DICT_PATH)
    previous = _load(baseline_path)

    lines: list[str] = []
    totals = {"added": 0, "removed": 0, "changed": 0}

    for section in _SECTIONS:
        added, removed, changed = _diff_section(
            previous.get(section, {}), current.get(section, {})
        )
        totals["added"] += len(added)
        totals["removed"] += len(removed)
        totals["changed"] += len(changed)

        for label, mapping in (("新增", added), ("删除", removed)):
            if not mapping:
                continue
            lines.append(f"[{section}] {label} {len(mapping)} 条：")
            for key in sorted(mapping):
                lines.append(f"    {key!r} -> {mapping[key]!r}")
                hits, total = _occurrences(key)
                for h in hits:
                    lines.append(h)
                if total > _OCCURRENCE_CAP:
                    lines.append(f"        … 共 {total} 处（仅显示前 {_OCCURRENCE_CAP} 处）")
            lines.append("")

        if changed:
            lines.append(f"[{section}] 修改 {len(changed)} 条：")
            for key in sorted(changed):
                old_val, new_val = changed[key]
                lines.append(f"    {key!r}")
                lines.append(f"        旧：{old_val!r}")
                lines.append(f"        新：{new_val!r}")
                hits, total = _occurrences(key)
                for h in hits:
                    lines.append(h)
                if total > _OCCURRENCE_CAP:
                    lines.append(f"        … 共 {total} 处（仅显示前 {_OCCURRENCE_CAP} 处）")
            lines.append("")

    summary = (
        "影响总览：新增 {added} 条、删除 {removed} 条、修改 {changed} 条。".format(**totals)
    )
    lines.insert(0, summary)
    lines.insert(1, "")
    return "\n".join(lines)


class Command(BaseCommand):
    help = "Diff current zh.json against a previous copy and list template impact."

    def add_arguments(self, parser):
        parser.add_argument(
            "--baseline",
            required=True,
            help="Path to the previous zh.json to diff against.",
        )
        parser.add_argument(
            "--output",
            help="Optional file path to write the report to (UTF-8).",
        )

    def handle(self, *args, **options):
        baseline = Path(options["baseline"])
        if not baseline.exists():
            raise SystemExit(f"基线文件不存在：{baseline}")

        report = build_report(baseline)
        self.stdout.write(report)

        out_path = options.get("output")
        if out_path:
            Path(out_path).write_text(report, encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"已写入 {out_path}"))