from rest_framework import serializers

from task.models import Task


class TaskSerializer(serializers.ModelSerializer):
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
        ]
        read_only_fields = ["id", "created_at", "updated_at", "completed_at"]
