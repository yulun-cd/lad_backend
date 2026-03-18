from rest_framework import viewsets

from daily_log.models import DailyLog
from daily_log.serializers import DailyLogSerializer


class DailyLogViewSet(viewsets.ModelViewSet):
    queryset = DailyLog.objects.all().order_by("-date", "-id")
    serializer_class = DailyLogSerializer
