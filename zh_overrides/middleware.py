"""HTML-safe Chinese localization middleware.

Reads zh.json (single source of truth) and translates only HTML text nodes:
tag names, attributes, comments, <script>/<style>/<textarea> contents and
entities are never modified. This covers hardcoded English in giant upstream
templates (base.html sidebar etc.) without copying those files, keeping the
drift surface minimal when upstream changes.

Two extra mechanisms live here:

1. Entity glue — when English text is split by ``&amp;`` (e.g.
   ``Drag &amp; drop``), consecutive data/entity segments are buffered,
   decoded as a whole and translated together; the original entity output is
   kept only when the combined text has no translation.
2. Client overlay injection — JS frameworks (Alpine x-text, htmx swaps,
   plain setMode()) overwrite server-rendered text after load. The middleware
   injects two deferred scripts before ``</body>``: the cached dictionary
   payload and zh-client.js, whose MutationObserver re-translates dynamic
   writes using the same dictionary.
"""

from __future__ import annotations

import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path

from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils.html import escape

from .payload_views import client_js_digest

_DICTIONARY: dict | None = None
_DIGEST: str | None = None

# Cookie that stores the per-user UI language. "en" forces the untouched
# upstream page; anything else (including no cookie) renders Chinese.
LANG_COOKIE = "zh_lang"

# Text inside these tags is passed through untouched (JS/CSS/user input).
_SKIP_TAGS = {"script", "style", "textarea"}

# Attributes that are human-visible UI text and safe to translate.
# data-label / data-action-label: 发布页 split-button 的模式文案由 JS 从这两个
# 属性读出并写入按钮文本，服务端直接译好即可，无需等客户端覆盖层。
_ATTR_ALWAYS = {"title", "aria-label", "placeholder", "data-label", "data-action-label"}


def load_dictionary() -> dict:
    """Load and compile zh.json once. Returns:

    exact:       {english: chinese} whole-text-node matching (phrases + words)
    exact_lower: {english lowercased: chinese} case-insensitive fallback
    subs:        [(english, chinese)] substring replacements
                 (multi-word phrases + safe tokens), longest source first
    """
    global _DICTIONARY
    if _DICTIONARY is not None:
        return _DICTIONARY

    data_path = Path(__file__).resolve().parent / "zh.json"
    with data_path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)

    phrases = raw.get("phrases", {})
    words = raw.get("words", {})
    tokens = raw.get("tokens", {})

    exact: dict[str, str] = {}
    exact.update(phrases)
    exact.update(words)
    exact_lower = {key.lower(): value for key, value in exact.items()}

    subs: dict[str, str] = {}
    subs.update(phrases)
    subs.update(tokens)
    ordered = sorted(subs.items(), key=lambda pair: len(pair[0]), reverse=True)

    _DICTIONARY = {
        "exact": exact,
        "exact_lower": exact_lower,
        "subs": ordered,
    }
    return _DICTIONARY


def reset_dictionary() -> None:
    """Test/management hook: force reload on next request."""
    global _DICTIONARY, _DIGEST
    _DICTIONARY = None
    _DIGEST = None


def dictionary_digest() -> str:
    """Short content hash of zh.json, used to cache-bust the payload URL."""
    global _DIGEST
    if _DIGEST is None:
        data_path = Path(__file__).resolve().parent / "zh.json"
        _DIGEST = hashlib.sha1(data_path.read_bytes()).hexdigest()[:12]
    return _DIGEST


def translate_text(text: str, dictionary: dict) -> str:
    stripped = text.strip()
    if stripped:
        replacement = dictionary["exact"].get(stripped)
        if replacement is None:
            replacement = dictionary["exact_lower"].get(stripped.lower())
        if replacement is not None:
            return text.replace(stripped, replacement, 1)
    for source, target in dictionary["subs"]:
        if source in text:
            text = text.replace(source, target)
    return text


class _ZhHTMLParser(HTMLParser):
    def __init__(self, dictionary: dict) -> None:
        # convert_charrefs=False keeps &entities; intact for reconstruction.
        super().__init__(convert_charrefs=False)
        self._dictionary = dictionary
        self.parts: list[str] = []
        self._skip_depth = 0
        # Buffered (raw, decoded) data/entity segments outside skip tags,
        # glued together so "Drag &amp; drop" can be translated as one unit.
        self._pending: list[tuple[str, str]] = []

    # -- entity glue -------------------------------------------------------

    def _flush_pending(self) -> None:
        if not self._pending:
            return
        combined = "".join(decoded for _raw, decoded in self._pending)
        translated = translate_text(combined, self._dictionary)
        if translated != combined:
            self.parts.append(translated)
        else:
            for raw, decoded in self._pending:
                if raw == decoded:
                    self.parts.append(translate_text(raw, self._dictionary))
                else:
                    self.parts.append(raw)
        self._pending = []

    # -- tag handlers ------------------------------------------------------

    def handle_starttag(self, tag, attrs):
        self._flush_pending()
        raw = self.get_starttag_text()
        if tag == "html":
            raw = raw.replace('lang="en"', 'lang="zh-CN"')
        raw = self._translate_attrs(tag, attrs, raw)
        self.parts.append(raw)
        if tag in _SKIP_TAGS:
            self._skip_depth += 1

    def _translate_attrs(self, tag, attrs, raw):
        attr_map = {name: value for name, value in attrs}
        input_type = (attr_map.get("type") or "").lower()
        for name, value in attrs:
            if value is None or not value:
                continue
            allowed = name in _ATTR_ALWAYS or (
                name == "value" and tag == "input" and input_type in {"submit", "button"}
            )
            if not allowed:
                continue
            new_value = translate_text(value, self._dictionary)
            if new_value == value:
                continue
            pattern = re.compile(r"(" + re.escape(name) + r"\s*=\s*)([\"'])" + re.escape(value) + r"\2")
            raw = pattern.sub(
                lambda m, nv=new_value: m.group(1) + m.group(2) + nv + m.group(2),
                raw,
                count=1,
            )
        return raw

    def handle_endtag(self, tag):
        self._flush_pending()
        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        self.parts.append(f"</{tag}>")

    def handle_startendtag(self, tag, attrs):
        self._flush_pending()
        raw = self.get_starttag_text()
        raw = self._translate_attrs(tag, attrs, raw)
        self.parts.append(raw)

    # -- text / entity handlers -------------------------------------------

    def handle_data(self, data):
        if self._skip_depth:
            self._flush_pending()
            self.parts.append(data)
        else:
            self._pending.append((data, data))

    def handle_entityref(self, name):
        if self._skip_depth:
            self._flush_pending()
            self.parts.append(f"&{name};")
        else:
            raw = f"&{name};"
            decoded = _ENTITY_REFS.get(name, raw)
            self._pending.append((raw, decoded))

    def handle_charref(self, name):
        if self._skip_depth:
            self._flush_pending()
            self.parts.append(f"&#{name};")
        else:
            raw = f"&#{name};"
            try:
                code = int(name[1:], 16) if name.lower().startswith("x") else int(name, 10)
                decoded = chr(code)
            except (ValueError, OverflowError):
                decoded = raw
            self._pending.append((raw, decoded))

    def handle_comment(self, data):
        self._flush_pending()
        self.parts.append(f"<!--{data}-->")

    def handle_decl(self, decl):
        self._flush_pending()
        self.parts.append(f"<!{decl}>")

    def unknown_decl(self, data):
        self._flush_pending()
        self.parts.append(f"<![{data}]>")

    def handle_pi(self, data):
        self._flush_pending()
        self.parts.append(f"<?{data}>")

    def close(self):
        self._flush_pending()
        super().close()


# Named entities that may glue an English phrase. &amp; is the common case;
# the rest keep the combined decode sane should a template ever use them.
_ENTITY_REFS = {
    "amp": "&",
    "lt": "<",
    "gt": ">",
    "quot": '"',
    "apos": "'",
    "nbsp": "\u00a0",
}


def _client_overlay_tags(request) -> str:
    nonce = getattr(request, "csp_nonce", "") or ""
    # client.js 走 Django 视图而非 /static/：构建期 collectstatic 用的是上游
    # settings（INSTALLED_APPS 无 zh_overrides），静态目录不会被收集。
    js_digest = client_js_digest()
    parts = [
        f'<script src="/zh-overrides/payload.js?v={dictionary_digest()}" nonce="{nonce}" defer></script>',
        f'<script src="/zh-overrides/client.js?v={js_digest}" nonce="{nonce}" defer></script>',
    ]
    return "".join(parts)


def _switch_url(request, target: str) -> str:
    """Current path with query params preserved and setlang=<target> added."""
    params = request.GET.copy()
    params["setlang"] = target
    query = params.urlencode()
    return request.path + ("?" + query if query else "")


def _lang_toggle_html(request) -> str:
    """Self-contained floating language pill.

    Rendered in BOTH languages so the user can always switch back. Inline
    styles only (no Tailwind dependency) and a plain anchor (no CSP impact).
    """
    english = request.COOKIES.get(LANG_COOKIE) == "en"
    target = "zh" if english else "en"
    href = escape(_switch_url(request, target))
    if english:
        label = "中"
        hint = "Switch to Chinese（切换为中文）"
        color, bg, border = "#b45309", "#fffbeb", "#fcd34d"
    else:
        label = "EN"
        hint = "Switch to English（切换为英文）"
        color, bg, border = "#44403c", "#ffffff", "#e7e5e4"
    return (
        f'<a id="zh-lang-toggle" href="{href}" title="{hint}" '
        f'aria-label="{hint}" style="position:fixed;right:12px;top:8px;'
        f"z-index:50;display:inline-flex;align-items:center;justify-content:center;"
        f"min-width:40px;height:28px;padding:0 12px;border-radius:9999px;"
        f"border:1px solid {border};background:{bg};color:{color};"
        f"font-size:13px;font-weight:700;text-decoration:none;"
        f'box-shadow:0 2px 8px rgba(0,0,0,0.15);">{label}</a>'
    )


class ZhLocalizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def _handle_setlang(self, request):
        """?setlang=en|zh: persist the choice in a cookie, redirect clean."""
        target = request.GET.get("setlang")
        if target not in {"en", "zh"}:
            target = "zh"
        params = request.GET.copy()
        del params["setlang"]
        url = request.path + ("?" + params.urlencode() if params else "")
        response = HttpResponseRedirect(url)
        response.set_cookie(
            LANG_COOKIE,
            target,
            max_age=31536000,
            path="/",
            samesite="Lax",
            secure=request.is_secure(),
        )
        return response

    def __call__(self, request):
        # Language switch action runs before the view and redirects.
        if "setlang" in request.GET:
            return self._handle_setlang(request)

        # Admin uses Django's official zh-hans translations for its chrome
        # (auth, allauth, built-in widgets). Activate only for /admin/ so the
        # main site keeps en-us date-formatting behaviour (explicit |date:"M j"
        # strings must not be localized). The active language is restored after
        # the view to avoid leaking across requests in threaded servers.
        from django.utils import translation
        is_admin = request.path.startswith("/admin/")
        saved_lang = translation.get_language() if is_admin else None
        if is_admin:
            translation.activate("zh-hans")
        try:
            response = self.get_response(request)
        finally:
            if is_admin:
                translation.activate(saved_lang)

        content_type = response.get("Content-Type", "")
        if "text/html" not in content_type:
            return response
        if getattr(response, "streaming", False):
            return response
        # Legal pages are bilingual by design; skip overlay / translation.
        if request.path in ("/privacy", "/legal", "/terms", "/data-deletion"):
            return response

        enabled = getattr(settings, "ZH_LOCALIZATION_ENABLED", True)
        # Debug bypass: append ?raw=1 to see the untouched upstream page.
        raw_bypass = request.GET.get("raw") == "1"
        # Per-user English choice: cookie zh_lang=en forces the upstream page.
        english_mode = request.COOKIES.get(LANG_COOKIE) == "en"
        translate = enabled and not raw_bypass and not english_mode

        charset = response.charset or "utf-8"
        content = response.content
        if not content:
            return response

        html_text = content.decode(charset)
        if translate:
            parser = _ZhHTMLParser(load_dictionary())
            parser.feed(html_text)
            parser.close()
            new_html = "".join(parser.parts)
        else:
            new_html = html_text

        if enabled and "</body>" in new_html and "zh-lang-toggle" not in new_html:
            new_html = new_html.replace("</body>", _lang_toggle_html(request) + "</body>", 1)

        # Dynamic-write overlay only in Chinese mode; in English mode the
        # observer must not run or it would translate JS writes back to zh.
        if translate and "</body>" in new_html and "zh-overrides/payload.js" not in new_html:
            new_html = new_html.replace("</body>", _client_overlay_tags(request) + "</body>", 1)

        new_content = new_html.encode(charset)
        response.content = new_content
        response["Content-Length"] = str(len(new_content))
        return response
