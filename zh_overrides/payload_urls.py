from django.urls import path

from .payload_views import batch_schedule_js, client_js, payload

urlpatterns = [
    path("payload.js", payload, name="zh-payload"),
    path("client.js", client_js, name="zh-client-js"),
    path("batch-schedule.js", batch_schedule_js, name="zh-batch-schedule-js"),
]
