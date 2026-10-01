"""Public privacy policy page (required by Meta business verification).

Rendered from a zh_overrides-local template so no upstream template is
touched. Mounted at /privacy/ from config/urls.py; intentionally not linked
from any navigation — direct URL access only.
"""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET


@require_GET
def privacy_policy(request: HttpRequest) -> HttpResponse:
    response = render(request, "zh_overrides/privacy.html")
    response["Cache-Control"] = "public, max-age=3600"
    return response
