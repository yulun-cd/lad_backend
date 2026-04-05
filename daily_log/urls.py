from django.urls import path
from rest_framework.routers import DefaultRouter

from daily_log.views import (
    DailyLogViewSet,
    DailySummaryView,
    EnergyOverTimeView,
    StreakView,
)

router = DefaultRouter()
router.register("daily-logs", DailyLogViewSet, basename="daily-log")

urlpatterns = [
    path("daily_summary/", DailySummaryView.as_view(), name="daily-summary"),
    path("streak/", StreakView.as_view(), name="streak"),
    path(
        "daily-logs/energy-over-time/",
        EnergyOverTimeView.as_view(),
        name="energy-over-time",
    ),
] + router.urls
