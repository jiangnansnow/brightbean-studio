"""URL routes for the zh-hans overlay, mounted via ROOT_URLCONF.

Imports the upstream ``config.urls`` urlpatterns unchanged and prepends the
overlay's own routes. Upstream urls.py is never edited, so upstream merges
stay conflict-free.

Overlay routes:
- ``/zh-overrides/payload.js`` — cached translation dictionary payload for the
  client overlay (injected by ZhLocalizationMiddleware)
- ``/privacy``, ``/legal``, ``/terms``, ``/data-deletion`` — public bilingual
  legal pages required by Meta business verification. Not linked from any
  navigation; direct URL access only. These URLs are crawled by Meta and must
  never disappear.
"""

from django.urls import include, path

from config.urls import urlpatterns as upstream_urlpatterns

from . import privacy_views

urlpatterns = [
    path("zh-overrides/", include("zh_overrides.payload_urls")),
    path("privacy", privacy_views.privacy_policy, name="privacy-policy"),
    path("legal", privacy_views.legal_center, name="legal-center"),
    path("terms", privacy_views.terms_of_service, name="terms-of-service"),
    path("data-deletion", privacy_views.data_deletion, name="data-deletion"),
] + upstream_urlpatterns
