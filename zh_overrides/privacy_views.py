"""Unified legal & compliance center (required by Meta business verification).

A single-page, two-column layout (sidebar + content) rendered from a
zh_overrides-local template so no upstream template is touched. Mounted at
/legal/, /privacy/, /terms/ from config/urls.py — all three URLs serve the
same page, each auto-positioning to its section. Intentionally not linked
from any navigation; direct URL access only.
"""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

_TEMPLATE = "zh_overrides/legal.html"


def _render(request: HttpRequest, scroll_to: str) -> HttpResponse:
    response = render(request, _TEMPLATE, {"scroll_to": scroll_to})
    response["Cache-Control"] = "public, max-age=3600"
    return response


@require_GET
def legal_center(request: HttpRequest) -> HttpResponse:
    return _render(request, "entity")


@require_GET
def privacy_policy(request: HttpRequest) -> HttpResponse:
    return _render(request, "privacy")


@require_GET
def terms_of_service(request: HttpRequest) -> HttpResponse:
    return _render(request, "terms")


@require_GET
def data_deletion(request: HttpRequest) -> HttpResponse:
    response = render(request, "zh_overrides/data_deletion.html")
    response["Cache-Control"] = "public, max-age=3600"
    return response
