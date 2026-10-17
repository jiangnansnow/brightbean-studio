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
_TOKEN_WORD_RE = re.compile(r"[A-Za-z]{2,}")


def _tokens(source: str) -> Counter:
    return Counter(_TAG_RE.findall(source) + _VAR_RE.findall(source))


def _harmful_embedding(core: str, parent: str) -> bool:
    """``core`` 作为 ``parent`` 的子串出现，且其左/右紧邻字符是字母或下划线
    （即 core 嵌入在更长英文词或 snake_case 标识符内部，而非由空格/标点分隔
    的独立单词）。"""
    start = 0
    while True:
        idx = parent.find(core, start)
        if idx == -1:
            return False
        left = parent[idx - 1] if idx > 0 else ""
        right = parent[idx + len(core)] if idx + len(core) < len(parent) else ""
        if (left and (left.isalpha() or left == "_")) or (right and (right.isalpha() or right == "_")):
            return True
        start = idx + 1


def _check_token_embedding(base_dir: Path) -> list[tuple[str, list[str]]]:
    """检测 tokens 段中「会切碎更长英文词/标识符」的危险子串 token。

    仅 tokens 段参与子串替换（见 middleware.load_dictionary），任何去空格后
    是纯字母单词、且会嵌入更长英文词/蛇形标识符内部的 token（``posts`` →
    ``create_posts``/``Reposts``、``platform`` → ``platforms``）都会产生半中
    半英残片。这类词应移入 words 段做精确匹配，或用「键值相同」词条保护。

    返回 [(token, [父词...]), ...]，父词为 zh.json 中把该 token 作为「有害
    子串」包含在内的其它源词（phrases/words/tokens 的 key）。
    """
    zh_path = base_dir / "zh_overrides" / "zh.json"
    if not zh_path.exists():
        return []
    data = json.loads(zh_path.read_text(encoding="utf-8"))
    sources: dict[str, str] = {}
    for section in ("phrases", "words", "tokens"):
        for key in data.get(section, {}):
            sources.setdefault(key, section)

    findings: list[tuple[str, list[str]]] = []
    for tok in data.get("tokens", {}):
        # 仅检测「无首尾空格」的纯字母 token：这类 token 无词界锚定，会嵌入
        # 连续字母/下划线串；带前导/后置空格的量词/前缀（" minutes"、"Add "）
        # 已有锚定，危害小，跳过。
        if tok != tok.strip() or not _TOKEN_WORD_RE.fullmatch(tok):
            continue
        parents = sorted(s for s in sources if s != tok and _harmful_embedding(tok, s))
        if parents:
            findings.append((tok, parents))
    return findings


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
        self.stdout.write(self.style.WARNING("tokens 子串嵌入检测（会切碎长词的 token，建议移入 words 段或键值保护）："))
        token_findings = _check_token_embedding(base_dir)
        if not token_findings:
            self.stdout.write(self.style.SUCCESS("[OK] tokens 段无危险子串"))
        else:
            for tok, parents in token_findings:
                shown = ", ".join(parents[:8])
                more = "" if len(parents) <= 8 else f" …共 {len(parents)} 个"
                self.stdout.write(
                    self.style.WARNING(f"[TOKEN] {tok!r} 嵌入：{shown}{more}")
                )

        self.stdout.write("")
        summary = f"Checked {checked} override file(s); {problems} problem(s)."
        if problems:
            self.stdout.write(self.style.ERROR(summary))
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS(summary))
