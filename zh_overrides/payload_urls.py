from django.urls import path

from .payload_views import payload

urlpatterns = [
    path("payload.js", payload, name="zh-payload"),
]
