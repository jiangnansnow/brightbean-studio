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


# --- zh-client.js -----------------------------------------------------------
# 构建期 collectstatic 用上游 config.settings.production 运行，其
# INSTALLED_APPS 不含 zh_overrides，因此本 app 的 static/ 目录永远不会被收集，
# 线上 /static/zh_overrides/zh-client.js 必然 404。改由本视图直接按文件内容
# 提供服务，与 payload.js 同源同缓存策略，彻底绕开 collectstatic。

_CLIENT_JS: tuple[str, str] | None = None


def _build_client_js() -> tuple[str, str]:
    global _CLIENT_JS
    if _CLIENT_JS is not None:
        return _CLIENT_JS

    import hashlib

    js_path = Path(__file__).resolve().parent / "static" / "zh_overrides" / "zh-client.js"
    raw_bytes = js_path.read_bytes()
    digest = hashlib.sha1(raw_bytes).hexdigest()[:12]
    _CLIENT_JS = (digest, raw_bytes.decode("utf-8"))
    return _CLIENT_JS


def client_js_digest() -> str:
    return _build_client_js()[0]


@require_GET
def client_js(request: HttpRequest) -> HttpResponse:
    _digest, body = _build_client_js()
    response = HttpResponse(body, content_type="application/javascript; charset=utf-8")
    response["Cache-Control"] = "public, max-age=31536000, immutable"
    response["X-Content-Type-Options"] = "nosniff"
    return response
