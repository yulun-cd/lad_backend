from datetime import timedelta

from django.utils import timezone
from django.db.models.functions import TruncDate
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from daily_log.models import DailyLog
from daily_log.serializers import DailyLogSerializer
from task.models import Task


class DailyLogViewSet(viewsets.ModelViewSet):
    serializer_class = DailyLogSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "put", "delete", "head", "options"]

    def get_queryset(self):
        return DailyLog.objects.filter(user=self.request.user).order_by("-date", "-id")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class DailySummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)

        completed_today_count = Task.objects.filter(
            user=request.user,
            completed_at__date=today,
        ).count()

        yesterday_log = DailyLog.objects.filter(
            user=request.user,
            date=yesterday,
        ).first()
        today_log = DailyLog.objects.filter(
            user=request.user,
            date=today,
        ).first()

        return Response(
            {
                "tasks_completed_today": completed_today_count,
                "yesterday_daily_log": (
                    DailyLogSerializer(yesterday_log).data if yesterday_log else None
                ),
                "today_daily_log": (
                    DailyLogSerializer(today_log).data if today_log else None
                ),
            }
        )


class StreakView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.localdate()
        completed_dates = set(
            Task.objects.filter(
                user=request.user,
                completed_at__isnull=False,
            )
            .annotate(completed_day=TruncDate("completed_at"))
            .values_list("completed_day", flat=True)
            .distinct()
        )

        streak = 0
        current_day = today
        while current_day in completed_dates:
            streak += 1
            current_day -= timedelta(days=1)

        return Response({"streak": streak})
