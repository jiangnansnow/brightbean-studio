"""Translation regression snapshot for the Chinese overlay.

The overlay's ``load_dictionary()`` + ``translate_text()`` translate every
upstream ``templates/**/*.html`` text node. Changing ``zh.json`` can change an
existing translation (a "改错" regression), and mimicry of the exact-match /
substring rules makes such breakage hard to review by eye.

This test freezes the translated output of every upstream template text node
into a JSON baseline. On each run it re-computes the mapping and diffs against
the baseline, failing when a *previously-translated* node now translates to a
different string (e.g. a phrase was deleted, re-keyed, or a token now
substring-hits a longer sentence).

Baseline file: ``zh_overrides/tests/fixtures/translation_snapshot.json``.
First run writes the baseline and skips. To re-baseline after a deliberate,
reviewed change, delete that file and re-run.
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest
from django.conf import settings

from zh_overrides.middleware import load_dictionary, translate_text

_BASELINE = Path(__file__).resolve().parent / "fixtures" / "translation_snapshot.json"

# Text inside these tags is never translated by the middleware.
_SKIP_TAGS = {"script", "style", "textarea"}

# Upstream templates never translated at runtime (sent as email, not HTTP).
_EXCLUDED_PATH_PARTS = {"/email/"}

# Legally/deliberately-excluded templates (kept for clarity even though the
# copies live in zh_overrides/templates, not upstream templates/).
_EXCLUDED_NAMES = {"legal.html", "data_deletion.html"}

_ASCII = re.compile(r"[A-Za-z]")


class _TextExtractor(HTMLParser):
    """Collect text nodes the same way the middleware sees them (entities decoded)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.nodes: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if not self._skip_depth:
            self.nodes.append(data)


def _extract_text_nodes(html: str) -> list[str]:
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    return parser.nodes


def _template_files() -> list[Path]:
    root = Path(settings.BASE_DIR) / "templates"
    files = []
    for template in sorted(root.rglob("*.html")):
        rel = template.relative_to(root).as_posix()
        if any(part in rel for part in _EXCLUDED_PATH_PARTS):
            continue
        if template.name in _EXCLUDED_NAMES:
            continue
        files.append(template)
    return files


def _collect() -> dict[str, dict[str, str]]:
    """Map {relative_template_path: {english_text: translated_text}}."""
    dictionary = load_dictionary()
    result: dict[str, dict[str, str]] = {}
    root = Path(settings.BASE_DIR) / "templates"
    for template in _template_files():
        per_file: dict[str, str] = {}
        for node in _extract_text_nodes(template.read_text(encoding="utf-8", errors="replace")):
            stripped = node.strip()
            if len(stripped) < 2 or not _ASCII.search(stripped):
                continue
            per_file[stripped] = translate_text(stripped, dictionary)
        if per_file:
            result[template.relative_to(root).as_posix()] = per_file
    return result


def test_translation_snapshot():
    current = _collect()

    if not _BASELINE.exists():
        _BASELINE.parent.mkdir(parents=True, exist_ok=True)
        _BASELINE.write_text(
            json.dumps({"files": current}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        pytest.skip(
            f"翻译快照基线已生成（{len(current)} 个模板）。"
            "再次运行即开始回归比对。"
        )

    baseline = json.loads(_BASELINE.read_text(encoding="utf-8"))["files"]

    changed: list[str] = []
    added: list[str] = []
    removed: list[str] = []

    for rel, current_map in sorted(current.items()):
        old_map = baseline.get(rel, {})
        for key, new_zh in sorted(current_map.items()):
            if key not in old_map:
                added.append(f"    + {rel} :: {key!r} -> {new_zh!r}")
            elif old_map[key] != new_zh:
                changed.append(
                    f"    ~ {rel} :: {key!r}\n"
                    f"        old: {old_map[key]!r}\n"
                    f"        new: {new_zh!r}"
                )
        for key in sorted(old_map):
            if key not in current_map:
                removed.append(f"    - {rel} :: {key!r}")

    # Only a translation *change* is a regression the dictionary can cause.
    # NEW (upstream added text) and REMOVED (upstream deleted text) are drift,
    # already surfaced by `manage.py zhcheck`; report them but do not fail.
    if added or removed:
        print(f"\n[翻译快照] 新增文本节点 {len(added)} 条、消失文本节点 {len(removed)} 条：")
        print("\n".join(removed + added))
    if changed:
        message = (
            f"翻译快照回归：{len(changed)} 条已有翻译被改动（疑似 zh.json 改错）\n"
            + "\n".join(changed)
        )
        raise AssertionError(message)