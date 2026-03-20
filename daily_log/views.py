from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from daily_log.models import DailyLog
from daily_log.serializers import DailyLogSerializer


class DailyLogViewSet(viewsets.ModelViewSet):
    serializer_class = DailyLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DailyLog.objects.filter(user=self.request.user).order_by("-date", "-id")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
