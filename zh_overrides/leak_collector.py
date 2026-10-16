"""Runtime leak collector for the Chinese overlay.

Captures English text nodes that the dictionary did not translate at all, so
missing phrases can be backfilled later without guessing. Disabled by default:
only when ``ZH_LEAK_COLLECT_ENABLED`` is true does the middleware record leaks,
appending one JSON line per unique text to a local file (never the database).

The collector is intentionally dumb and dependency-free so it can be imported
from the middleware hot path without cost when disabled.
"""

from __future__ import annotations

import json
import re
import threading

_LETTER = re.compile(r"[A-Za-z]")
# Code / template / URL fragments are never real UI copy; skip them.
_BAD = re.compile(r"[{}<>\[\]\\_]|https?://|www\.|\{\{|\{%|%\}")

_LOCK = threading.Lock()
_SEEN: set[str] = set()


def _enabled() -> bool:
    from django.conf import settings

    return bool(getattr(settings, "ZH_LEAK_COLLECT_ENABLED", False))


def _collect_dir():
    from django.conf import settings

    configured = getattr(settings, "ZH_LEAK_COLLECT_DIR", "") or ""
    if configured:
        from pathlib import Path

        return Path(configured)
    import tempfile
    from pathlib import Path

    return Path(tempfile.gettempdir()) / "brightbean_zh_leaks"


def _qualifies(text: str) -> bool:
    t = text.strip()
    if len(t) < 2 or len(t) > 200:
        return False
    if not _LETTER.search(t):
        return False
    if _BAD.search(t):
        return False
    words = [w for w in re.split(r"\s+", t) if w]
    if len(words) < 2:
        return False
    # At least one real (mostly alphabetic, >=2 chars) word.
    if not any(len(w) >= 2 and sum(c.isalpha() for c in w) >= 2 for w in words):
        return False
    # Skip all-caps acronym blobs (API, RSS, CSV, HTML) — those are markers,
    # not translatable prose.
    if t.isupper():
        return False
    return True


def record(text: str) -> None:
    """Record one untranslated text node (no-op unless enabled)."""
    if not _enabled():
        return
    if not _qualifies(text):
        return
    key = text.strip()
    with _LOCK:
        if key in _SEEN:
            return
        _SEEN.add(key)
        try:
            d = _collect_dir()
            d.mkdir(parents=True, exist_ok=True)
            with (d / "leaks.jsonl").open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"text": key}, ensure_ascii=False) + "\n")
        except Exception:
            # Leak collection must never break the response path.
            pass


def reset() -> None:
    """Test hook: clear the in-memory dedupe set."""
    with _LOCK:
        _SEEN.clear()