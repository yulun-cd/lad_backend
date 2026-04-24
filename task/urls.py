from django.urls import path
from rest_framework.routers import DefaultRouter

from task.views import (
    TaskCompletionTimeView,
    TaskFilterView,
    TaskTagViewSet,
    TaskViewSet,
)

router = DefaultRouter()
router.register("tasks", TaskViewSet, basename="task")
router.register("task-tags", TaskTagViewSet, basename="task-tag")

urlpatterns = [
    path(
        "tasks/completion-time/",
        TaskCompletionTimeView.as_view(),
        name="task-completion-time",
    ),
    path(
        "tasks/filter/",
        TaskFilterView.as_view(),
        name="task-filter",
    ),
] + router.urls
