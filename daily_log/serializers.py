from datetime import date

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
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]

    def validate_date(self, value):
        if value > date.today():
            raise serializers.ValidationError("Date cannot be in the future.")
        return value

    def validate(self, data):
        user = self.context["request"].user
        date_value = data.get("date")
        instance = self.instance

        if date_value and user:
            existing = DailyLog.objects.filter(user=user, date=date_value)
            if instance:
                existing = existing.exclude(pk=instance.pk)
            if existing.exists():
                raise serializers.ValidationError(
                    "A daily log for this date already exists."
                )
        return data
