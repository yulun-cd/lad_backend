from rest_framework import serializers

from daily_log.models import DailyLog


class DailyLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyLog
        fields = [
            "id",
            "date",
            "overall",
            "energy",
            "emotion",
            "productivity",
            "description",
        ]
        read_only_fields = ["id"]
