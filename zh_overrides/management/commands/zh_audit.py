"""Audit zh.json for suspicious translations, with template locations.

Scans every entry across the ``phrases`` / ``words`` / ``tokens`` sections and
flags entries whose *target* (Chinese) looks wrong. Each finding is annotated
with where the English *source* appears in the rendered templates (file:line +
surrounding HTML), so a non-developer can open that page and press F12 to see
the actual on-screen context and judge the correct translation.

Detected categories (highest signal first):

- ERROR  empty      : target is blank (e.g. ``" from now": ""``).
- ERROR  placeholders: target leaks ``{{ }}`` / ``{% %}`` template syntax.
- WARN   untranslated: target is byte-identical to its source (not translated).
- WARN   residue     : target still contains a run of >=3 ASCII letters that is
                      not a known proper noun / platform / tech term.
- SUSPECT short      : a long source collapses to almost no Chinese characters.

Occurrence scan honesty note: it searches server-rendered HTML templates only.
Text emitted purely by client JS (Alpine/htmx writes) is not traced here; those
would need a separate search under ``static/``.

Usage:
    python manage.py zh_audit                       # human report to stdout
    python manage.py zh_audit --output 汉化译文体检.txt
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

_DICT_PATH = Path(__file__).resolve().parents[2] / "zh.json"
_SECTIONS = ("phrases", "words", "tokens")

# Proper nouns / brands / tech terms that legitimately stay in English inside
# an otherwise-Chinese UI. case-folded for matching.
_WHITELIST = {
    "brightbean", "brightbean studio", "ysec", "studio",
    # platforms & brands
    "tiktok", "facebook", "instagram", "youtube", "pinterest", "mastodon",
    "bluesky", "linkedin", "whatsapp", "threads", "snapchat", "twitter",
    "meta", "google", "shopify", "unsplash", "pexels", "pixabay", "canva",
    "trustpilot", "giphy", "zapier", "stripe", "dev",
    # tech / formats / org names
    "api", "oauth", "sla", "rss", "csv", "tsv", "url", "uri", "http", "https",
    "json", "html", "xml", "webhook", "coppa", "png", "jpg", "jpeg", "gif",
    "mp4", "svg", "reel", "reels", "duet", "stitch", "protocol", "markdown",
    "webp", "utc", "iana", "django", "mcp", "saas", "shorts", "feed",
    "example", "com",
}

_EN_RUN = re.compile(r"[A-Za-z]{3,}")
_PLACEHOLDERS = re.compile(r"\{\{|\{%|%}|}}")
_CJK = re.compile(r"[\u4e00-\u9fff]")

# Occurrence scanning
_LEGAL_NAMES = {"legal.html", "data_deletion.html"}
_EMAIL_PART = "/email/"
_OCCURRENCE_CAP = 4
_CONTEXT_LINES = 1


def _word_count(text: str) -> int:
    return sum(1 for w in text.split() if sum(c.isalpha() for c in w) >= 2)


def _english_residues(value: str) -> list[str]:
    # 先剥离 HTML 实体（&middot; / &rsaquo; / &times; 等）：实体名不是 UI 英文，
    # 且中间件不解码它们、译文内也按原样保留，不能当作漏译残片误报。
    cleaned = re.sub(r"&[a-zA-Z]+;", " ", value)
    seen: list[str] = []
    for match in _EN_RUN.finditer(cleaned):
        frag = match.group(0)
        if frag.lower() in _WHITELIST:
            continue
        if frag not in seen:
            seen.append(frag)
    return seen


def _template_roots() -> list[Path]:
    base = Path(settings.BASE_DIR)
    return [base / "templates", base / "zh_overrides" / "templates"]


def _is_skipped(rel: str) -> bool:
    return _EMAIL_PART in rel or Path(rel).name in _LEGAL_NAMES


def _occurrences(key: str) -> tuple[list[str], int]:
    """Return (block_strings, total_hits) for the English source ``key``.

    Each block shows the matched line plus surrounding lines so the whole
    sentence is visible; comment-only lines are skipped (they are not UI text).
    """
    hits: list[str] = []
    total = 0
    for root in _template_roots():
        if not root.exists():
            continue
        for template in sorted(root.rglob("*.html")):
            rel = template.relative_to(root).as_posix()
            if _is_skipped(rel):
                continue
            lines = template.read_text(encoding="utf-8", errors="replace").splitlines()
            for i, line in enumerate(lines):
                if key not in line:
                    continue
                if line.lstrip().startswith("<!--"):
                    continue
                total += 1
                if total > _OCCURRENCE_CAP:
                    continue
                lo = max(0, i - _CONTEXT_LINES)
                hi = min(len(lines), i + _CONTEXT_LINES + 1)
                block = []
                for j in range(lo, hi):
                    marker = "→" if j == i else " "
                    block.append(f"{marker} {rel}:{j + 1}  {lines[j].strip()[:150]}")
                hits.append("\n".join(block))
    return hits, total


def audit() -> dict:
    """Return a dict of findings keyed by category, each a list of dicts."""
    raw = json.loads(_DICT_PATH.read_text(encoding="utf-8"))
    findings: dict[str, list[dict]] = {
        "empty": [],
        "placeholders": [],
        "untranslated": [],
        "residue": [],
        "short": [],
    }

    for section in _SECTIONS:
        for key, value in raw.get(section, {}).items():
            value = value or ""
            entry = {"section": section, "key": key, "value": value}
            stripped = value.strip()

            if not stripped:
                findings["empty"].append(entry)
                continue
            if _PLACEHOLDERS.search(value):
                findings["placeholders"].append(entry)
                continue
            if stripped.casefold() == key.strip().casefold():
                findings["untranslated"].append(entry)
                continue

            residues = _english_residues(value)
            if residues:
                findings["residue"].append(dict(entry, residues=residues))

            if _word_count(key) >= 5 and len(_CJK.findall(value)) <= 2:
                findings["short"].append(dict(entry, cjk=len(_CJK.findall(value))))

    return findings


def _append_occurrences(lines: list[str], key: str, indent: str) -> None:
    blocks, total = _occurrences(key)
    if not blocks:
        lines.append(f"{indent}出现位置：未在模板可见文本中找到（疑似冗余/孤儿词条，仅在 JS 中动态出现需另查 static/）。")
        return
    lines.append(f"{indent}出现位置：")
    for block in blocks:
        for line in block.splitlines():
            lines.append(f"{indent}  {line}")
    if total > _OCCURRENCE_CAP:
        lines.append(f"{indent}  … 共 {total} 处（仅显示前 {_OCCURRENCE_CAP} 处）")


def _format(findings: dict) -> str:
    lines: list[str] = []
    labels = {
        "empty": ("ERROR", "空译文（译文为空）"),
        "placeholders": ("ERROR", "译文含模板占位符 {{ }} / {% %}"),
        "untranslated": ("WARN", "译文与原文相同（未翻译）"),
        "residue": ("WARN", "译文残留英文片段"),
        "short": ("SUSPECT", "译文相对原文异常缩短"),
    }
    total = 0
    for category, (level, label) in labels.items():
        items = findings[category]
        total += len(items)
        lines.append(f"[{level}] {label}：{len(items)} 条")
        for it in items:
            key = it["key"].replace("\n", "\\n")
            val = it["value"].replace("\n", "\\n")
            extra = ""
            if "residues" in it:
                extra = f"  ← 残留英文：{', '.join(it['residues'])}"
            elif "cjk" in it:
                extra = f"  ← 汉字数：{it['cjk']}"
            lines.append(f"    [{it['section']}] {key!r} -> {val!r}{extra}")
            _append_occurrences(lines, it["key"], "        ")
        lines.append("")
    lines.append(f"共 {total} 条疑似异常，供人工复核（不自动修改）。")
    return "\n".join(lines)


class Command(BaseCommand):
    help = "Audit zh.json for suspicious/broken translations (advisory review list)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            help="Optional file path to write the report to (UTF-8).",
        )

    def handle(self, *args, **options):
        report = _format(audit())
        self.stdout.write(report)

        out_path = options.get("output")
        if out_path:
            Path(out_path).write_text(report, encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"已写入 {out_path}"))