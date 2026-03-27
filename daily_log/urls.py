from django.urls import path
from rest_framework.routers import DefaultRouter

from daily_log.views import DailyLogViewSet, DailySummaryView, StreakView

router = DefaultRouter()
router.register("daily-logs", DailyLogViewSet, basename="daily-log")

urlpatterns = [
    path("daily_summary/", DailySummaryView.as_view(), name="daily-summary"),
    path("streak/", StreakView.as_view(), name="streak"),
] + router.urls
