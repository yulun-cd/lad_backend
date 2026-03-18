from rest_framework.routers import DefaultRouter

from daily_log.views import DailyLogViewSet

router = DefaultRouter()
router.register("daily-logs", DailyLogViewSet, basename="daily-log")

urlpatterns = router.urls
