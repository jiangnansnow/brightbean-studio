"""zh_overrides 批量入队（文件夹模式）路由，挂在工作区前缀下。"""

from django.urls import path

from . import batch_views

app_name = "zh_batch"

urlpatterns = [
    path("folders/", batch_views.folders, name="folders"),
    path("plan/", batch_views.plan, name="plan"),
    path("enqueue/", batch_views.enqueue, name="enqueue"),
    path("active/", batch_views.active, name="active"),
    path("batches/<uuid:batch_id>/clear/", batch_views.clear, name="clear"),
]
