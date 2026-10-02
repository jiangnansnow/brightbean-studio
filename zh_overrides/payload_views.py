"""Serve the compiled zh.json dictionary as a cacheable JS payload.

The client overlay (zh-client.js) reads ``window.__ZH__`` and re-translates
text written dynamically by Alpine/htmx/vanilla JS. The URL carries a short
content hash so browsers can cache the payload immutably; editing zh.json
changes the URL injected by the middleware.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_GET

_PAYLOAD: tuple[str, str] | None = None


def _build_payload() -> tuple[str, str]:
    global _PAYLOAD
    if _PAYLOAD is not None:
        return _PAYLOAD

    data_path = Path(__file__).resolve().parent / "zh.json"
    raw_bytes = data_path.read_bytes()
    raw = json.loads(raw_bytes.decode("utf-8"))

    phrases = raw.get("phrases", {})
    words = raw.get("words", {})
    tokens = raw.get("tokens", {})

    exact: dict[str, str] = {}
    exact.update(phrases)
    exact.update(words)
    lower = {key.lower(): value for key, value in exact.items()}

    subs: dict[str, str] = {}
    subs.update(phrases)
    subs.update(tokens)
    ordered = sorted(subs.items(), key=lambda pair: len(pair[0]), reverse=True)

    import hashlib

    digest = hashlib.sha1(raw_bytes).hexdigest()[:12]
    data = {
        "v": digest,
        "exact": exact,
        "lower": lower,
        "subs": ordered,
    }
    body = "window.__ZH__ = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";"
    _PAYLOAD = (digest, body)
    return _PAYLOAD


@require_GET
def payload(request: HttpRequest) -> HttpResponse:
    _digest, body = _build_payload()
    response = HttpResponse(body, content_type="application/javascript; charset=utf-8")
    response["Cache-Control"] = "public, max-age=31536000, immutable"
    response["X-Content-Type-Options"] = "nosniff"
    return response
