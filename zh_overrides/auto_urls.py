"""zh_overrides 文件夹自动候补排期路由，挂在工作区前缀下。"""

from django.urls import path

from . import auto_views

app_name = "zh_auto"

urlpatterns = [
    path("folders/", auto_views.folders, name="folders"),
    path("panel/", auto_views.panel, name="panel"),
    path("enable/", auto_views.enable, name="enable"),
    path("disable/", auto_views.disable, name="disable"),
    path("social-toggle/", auto_views.social_toggle_state, name="social_toggle_state"),
    path("social-toggle/flip/", auto_views.social_toggle, name="social_toggle"),
    path("active/", auto_views.active, name="active"),
    path("batches/<uuid:batch_id>/clear/", auto_views.clear, name="clear"),
]
