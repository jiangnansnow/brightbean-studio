from django.urls import path

from .payload_views import client_js, payload

urlpatterns = [
    path("payload.js", payload, name="zh-payload"),
    path("client.js", client_js, name="zh-client-js"),
]
