"""HTML-safe Chinese localization middleware.

Reads zh.json (single source of truth) and translates only HTML text nodes:
tag names, attributes, comments, <script>/<style>/<textarea> contents and
entities are never modified. This covers hardcoded English in giant upstream
templates (base.html sidebar etc.) without copying those files, keeping the
drift surface minimal when upstream changes.
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path

from django.conf import settings

_DICTIONARY: dict | None = None

# Text inside these tags is passed through untouched (JS/CSS/user input).
_SKIP_TAGS = {"script", "style", "textarea"}

# Attributes that are human-visible UI text and safe to translate.
_ATTR_ALWAYS = {"title", "aria-label", "placeholder"}


def load_dictionary() -> dict:
    """Load and compile zh.json once. Returns:

    exact: {english: chinese} for whole-text-node matching (phrases + words)
    subs:  [(english, chinese)] substring replacements
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

    subs: dict[str, str] = {}
    subs.update(phrases)
    subs.update(tokens)
    ordered = sorted(subs.items(), key=lambda pair: len(pair[0]), reverse=True)

    _DICTIONARY = {"exact": exact, "subs": ordered}
    return _DICTIONARY


def reset_dictionary() -> None:
    """Test/management hook: force reload on next request."""
    global _DICTIONARY
    _DICTIONARY = None


def translate_text(text: str, dictionary: dict) -> str:
    stripped = text.strip()
    if stripped:
        replacement = dictionary["exact"].get(stripped)
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

    def handle_starttag(self, tag, attrs):
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
        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        self.parts.append(f"</{tag}>")

    def handle_startendtag(self, tag, attrs):
        raw = self.get_starttag_text()
        raw = self._translate_attrs(tag, attrs, raw)
        self.parts.append(raw)

    def handle_data(self, data):
        if self._skip_depth:
            self.parts.append(data)
        else:
            self.parts.append(translate_text(data, self._dictionary))

    def handle_entityref(self, name):
        self.parts.append(f"&{name};")

    def handle_charref(self, name):
        self.parts.append(f"&#{name};")

    def handle_comment(self, data):
        self.parts.append(f"<!--{data}-->")

    def handle_decl(self, decl):
        self.parts.append(f"<!{decl}>")

    def unknown_decl(self, data):
        self.parts.append(f"<![{data}]>")

    def handle_pi(self, data):
        self.parts.append(f"<?{data}>")


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

        charset = response.charset or "utf-8"
        content = response.content
        if not content:
            return response

        parser = _ZhHTMLParser(load_dictionary())
        parser.feed(content.decode(charset))
        new_content = "".join(parser.parts).encode(charset)

        response.content = new_content
        response["Content-Length"] = str(len(new_content))
        return response
