"""Detect partial-translation residue in rendered template text nodes.

The leak collector only records text nodes the dictionary did not touch at all.
The far more damaging class of bug the user flagged is the *partial* one: a
full English sentence where a few words were substring-replaced (workspace →
工作区, members → 成员) but the rest stayed English, producing mixed-language
fragments like ``Reviewers are workspace 成员``.

This command walks every upstream template text node, runs it through the same
``translate_text`` the middleware uses, and reports cases where the result is
partly Chinese yet still contains a run of >=2 non-whitelisted English words —
i.e. sentences that were torn apart by piecemeal substitution instead of being
translated whole. Each finding is advisory: some hits are legitimate (proper
nouns, dynamic placeholders) and need human judgement, not blind replacement.

Usage:
    python manage.py zh_residue
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from zh_overrides.management.commands.zh_audit import _WHITELIST
from zh_overrides.middleware import load_dictionary, translate_text

_SKIP_TAGS = {"script", "style", "textarea"}
_CJK = re.compile(r"[\u4e00-\u9fff]")
_EMAIL_PART = "/email/"


class _TextExtractor(HTMLParser):
    """Collect text nodes; entities decoded for easier human review."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.nodes: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS and self._skip > 0:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.nodes.append(data)


def _residual_blocks(translated: str) -> list[str]:
    """返回译文里成串的英文词块（>=2 个连续英文词且含非白名单词）。"""
    cleaned = re.sub(r"&[a-zA-Z]+;", " ", translated)
    blocks = re.findall(r"[A-Za-z]{3,}(?:[ \t]+[A-Za-z]{3,})+", cleaned)
    result = []
    for block in blocks:
        words = re.findall(r"[A-Za-z]{3,}", block)
        if sum(1 for w in words if w.lower() not in _WHITELIST) >= 2:
            result.append(block)
    return result


def _line_of(content: str, stripped: str) -> int:
    # 取第一个"较长英文片段"作探针，避免用空白/标点误定位到模板结构行。
    m = re.search(r"[A-Za-z][A-Za-z0-9 &'\-\.·,]{12,}", stripped)
    probe = (m.group(0).strip() if m else "")[:40]
    if not probe:
        return 0
    lines = content.splitlines()
    for idx, line in enumerate(lines, 1):
        if probe in line:
            return idx
    for idx, line in enumerate(lines, 1):
        if probe[:20] in line:
            return idx
    return 0


def detect() -> list[dict]:
    dictionary = load_dictionary()
    base = Path(settings.BASE_DIR)
    finds: list[dict] = []
    for template in sorted((base / "templates").rglob("*.html")):
        rel = template.relative_to(base / "templates").as_posix()
        if _EMAIL_PART in rel:
            continue
        content = template.read_text(encoding="utf-8", errors="replace")
        # 剥掉 Django 模板标签/变量：它们是模板结构不是 UI 文本，且会被
        # HTMLParser 误当 data；缺省会把手写标签词（如 {% block title %}）
        # 误判成残片。
        clean = re.sub(r"\{%\s*comment\s*%\}[\s\S]*?\{%\s*endcomment\s*%\}", " ", content)
        clean = re.sub(r"\{%[\s\S]*?%\}", " ", clean)
        clean = re.sub(r"\{\{[\s\S]*?\}\}", " ", clean)
        clean = re.sub(r"\{#[\s\S]*?#\}", " ", clean)
        clean = re.sub(r"<!--[\s\S]*?-->", " ", clean)
        parser = _TextExtractor()
        parser.feed(clean)
        parser.close()
        for node in parser.nodes:
            stripped = node.strip()
            if len(stripped) < 4:
                continue
            translated = translate_text(stripped, dictionary)
            if translated == stripped:
                continue
            if not _CJK.search(translated):
                continue
            blocks = _residual_blocks(translated)
            if blocks:
                finds.append(
                    {
                        "file": rel,
                        "line": _line_of(content, stripped),
                        "source": stripped,
                        "translated": translated,
                        "blocks": blocks,
                    }
                )
    return finds


class Command(BaseCommand):
    help = "Detect partial-translation residue (mixed-language torn sentences)."

    def handle(self, *args, **options):
        findings = detect()
        if not findings:
            self.stdout.write(self.style.SUCCESS("未发现部分翻译残片。"))
            return

        for f in findings:
            self.stdout.write(f"[残片] {f['file']}:{f['line'] or '?'}")
            self.stdout.write(f"    原文: {f['source'][:160]}")
            self.stdout.write(f"    译文: {f['translated'][:160]}")
            self.stdout.write(f"    残留英文块: {', '.join(f['blocks'])}")
            self.stdout.write("")
        self.stdout.write(self.style.WARNING(f"共 {len(findings)} 处疑似残片，供人工复核。"))