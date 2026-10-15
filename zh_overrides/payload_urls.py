from django.urls import path

from .payload_views import auto_schedule_js, client_js, payload

urlpatterns = [
    path("payload.js", payload, name="zh-payload"),
    path("client.js", client_js, name="zh-client-js"),
    path("auto-schedule.js", auto_schedule_js, name="zh-auto-schedule-js"),
]
