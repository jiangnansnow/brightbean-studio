"""zh_overrides 文件夹自动排期路由，挂在工作区前缀下。"""

from django.urls import path

from . import auto_views

app_name = "zh_auto"

urlpatterns = [
    path("folders/", auto_views.folders, name="folders"),
    path("panel/", auto_views.panel, name="panel"),
    path("queue/", auto_views.queue, name="queue"),
    path("clear-media/", auto_views.clear_media, name="clear_media"),
    path("social-toggle/", auto_views.social_toggle_state, name="social_toggle_state"),
    path("social-toggle/flip/", auto_views.social_toggle, name="social_toggle"),
    path("active/", auto_views.active, name="active"),
    path("batches/<uuid:batch_id>/clear/", auto_views.clear, name="clear"),
]