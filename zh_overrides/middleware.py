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

_DICTIONARY: dict | None = None
_DIGEST: str | None = None

# Text inside these tags is passed through untouched (JS/CSS/user input).
_SKIP_TAGS = {"script", "style", "textarea"}

# Attributes that are human-visible UI text and safe to translate.
_ATTR_ALWAYS = {"title", "aria-label", "placeholder"}


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
                    self.parts.append(
                        translate_text(raw, self._dictionary)
                    )
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
            pattern = re.compile(
                r"(" + re.escape(name) + r"\s*=\s*)([\"'])"
                + re.escape(value) + r"\2"
            )
            raw = pattern.sub(
                lambda m: m.group(1) + m.group(2) + new_value + m.group(2),
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
                if name.lower().startswith("x"):
                    code = int(name[1:], 16)
                else:
                    code = int(name, 10)
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
    digest = dictionary_digest()
    static_url = getattr(settings, "STATIC_URL", "/static/")
    client_url = f"{static_url}zh_overrides/zh-client.js"
    parts = [
        f'<script src="/zh-overrides/payload.js?v={digest}" nonce="{nonce}" defer></script>',
        f'<script src="{client_url}" nonce="{nonce}" defer></script>',
    ]
    return "".join(parts)


class ZhLocalizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        content_type = response.get("Content-Type", "")
        if "text/html" not in content_type:
            return response
        if getattr(response, "streaming", False):
            return response
        # Django admin has its own i18n path; leave it to LANGUAGE_CODE.
        if request.path.startswith("/admin/"):
            return response
        if not getattr(settings, "ZH_LOCALIZATION_ENABLED", True):
            return response
        # Debug bypass: append ?raw=1 to see the untouched upstream page.
        if request.GET.get("raw") == "1":
            return response

        charset = response.charset or "utf-8"
        content = response.content
        if not content:
            return response

        html_text = content.decode(charset)
        parser = _ZhHTMLParser(load_dictionary())
        parser.feed(html_text)
        parser.close()
        new_html = "".join(parser.parts)

        # Inject the dynamic-write translation overlay once per page.
        if "</body>" in new_html and "zh-overrides/payload.js" not in new_html:
            overlay = _client_overlay_tags(request)
            new_html = new_html.replace("</body>", overlay + "</body>", 1)

        new_content = new_html.encode(charset)
        response.content = new_content
        response["Content-Length"] = str(len(new_content))
        return response
