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
        ]
        read_only_fields = ["id", "created_at", "updated_at", "completed_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            self.fields["tag"].queryset = TaskTag.objects.filter(
                created_by=request.user
            )
