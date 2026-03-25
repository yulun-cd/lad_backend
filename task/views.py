from django.db.models import Case, F, IntegerField, Value, When
from django.db.models.functions import Coalesce, Greatest
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from task.models import Task
from task.serializers import TaskSerializer


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "put", "delete", "head", "options"]

    def get_queryset(self):
        queryset = Task.objects.filter(user=self.request.user)
        status = self.request.query_params.get("status")

        if status:
            valid_statuses = {choice.value for choice in Task.Status}
            if status not in valid_statuses:
                raise ValidationError(
                    {
                        "status": [
                            "Invalid status. Choose one of: "
                            + ", ".join(sorted(valid_statuses))
                        ]
                    }
                )
            queryset = queryset.filter(status=status)

        return queryset.annotate(
            status_priority=Case(
                When(status=Task.Status.IN_PROGRESS, then=Value(0)),
                When(status=Task.Status.PENDING, then=Value(1)),
                When(status=Task.Status.COMPLETED, then=Value(2)),
                default=Value(3),
                output_field=IntegerField(),
            ),
            last_activity=Greatest(
                F("created_at"),
                Coalesce(F("updated_at"), F("created_at")),
            ),
        ).order_by("status_priority", "-last_activity", "-id")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
