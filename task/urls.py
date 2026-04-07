from rest_framework.routers import DefaultRouter

from task.views import TaskTagViewSet, TaskViewSet

router = DefaultRouter()
router.register("tasks", TaskViewSet, basename="task")
router.register("task-tags", TaskTagViewSet, basename="task-tag")

urlpatterns = router.urls
