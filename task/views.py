from django.db.models import Case, Count, F, IntegerField, Value, When
from django.db.models.functions import Coalesce, ExtractHour, Greatest
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from task.models import Task, TaskTag
from task.serializers import TaskSerializer, TaskTagSerializer


class TaskTagViewSet(viewsets.ModelViewSet):
    serializer_class = TaskTagSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "put", "delete", "head", "options"]

    def get_queryset(self):
        return TaskTag.objects.filter(created_by=self.request.user).order_by(
            "-created_at", "-id"
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

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

        tag_ids = self.request.query_params.getlist("tag")
        if tag_ids:
            if not all(tid.isdigit() for tid in tag_ids):
                raise ValidationError({"tag": ["Tag IDs must be positive integers."]})
            queryset = queryset.filter(tag_id__in=tag_ids)

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

    def perform_update(self, serializer):
        from datetime import timedelta

        previous_status = self.get_object().status
        instance = serializer.save()
        if (
            previous_status != Task.Status.COMPLETED
            and instance.status == Task.Status.COMPLETED
            and instance.recurrence_interval is not None
        ):
            Task.objects.create(
                user=instance.user,
                name=instance.name,
                description=instance.description,
                energy_level=instance.energy_level,
                tag=instance.tag,
                date=instance.date + timedelta(days=instance.recurrence_interval),
                recurrence_interval=instance.recurrence_interval,
                recurrence_origin=instance,
                status=Task.Status.PENDING,
                done=False,
            )


class TaskCompletionTimeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        counts_by_hour = (
            Task.objects.filter(user=request.user, completed_at__isnull=False)
            .annotate(hour=ExtractHour("completed_at"))
            .values("hour")
            .annotate(count=Count("id"))
        )

        hour_map = {row["hour"]: row["count"] for row in counts_by_hour}
        data = [{"hour": h, "count": hour_map.get(h, 0)} for h in range(24)]
        return Response(data)
