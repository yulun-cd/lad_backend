from rest_framework import serializers

from task.models import Task, TaskTag


class TaskTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskTag
        fields = ["id", "name", "color", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_color(self, value):
        from django.core.exceptions import ValidationError as DjangoValidationError
        from task.models import validate_hex_color

        try:
            validate_hex_color(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message)
        return value


class TaskSerializer(serializers.ModelSerializer):
    tag = serializers.PrimaryKeyRelatedField(
        queryset=TaskTag.objects.none(),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = Task
        fields = [
            "id",
            "name",
            "done",
            "status",
            "created_at",
            "updated_at",
            "completed_at",
            "description",
            "energy_level",
            "tag",
            "date",
            "recurrence_interval",
            "recurrence_origin",
            "position",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "completed_at",
            "recurrence_origin",
        ]

    def validate_recurrence_interval(self, value):
        if value is not None and value < 1:
            raise serializers.ValidationError(
                "Recurrence interval must be at least 1 day."
            )
        return value

    def validate_position(self, value):
        if value is not None and value < 1:
            raise serializers.ValidationError(
                "Position must be a positive integer (>= 1)."
            )
        return value

    def validate(self, attrs):
        interval = attrs.get(
            "recurrence_interval",
            self.instance.recurrence_interval if self.instance else None,
        )
        date = attrs.get("date", self.instance.date if self.instance else None)
        if interval is not None and date is None:
            raise serializers.ValidationError(
                {"date": "A date is required when setting a recurrence interval."}
            )
        return attrs

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            self.fields["tag"].queryset = TaskTag.objects.filter(
                created_by=request.user
            )
