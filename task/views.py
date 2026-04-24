from django.db import transaction
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
        ).order_by(
            "status_priority",
            F("position").asc(nulls_last=True),
            "-last_activity",
            "id",
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        tasks = serializer.data
        groups = [
            {"status": Task.Status.IN_PROGRESS, "tasks": []},
            {"status": Task.Status.PENDING, "tasks": []},
            {"status": Task.Status.COMPLETED, "tasks": []},
        ]
        bucket = {g["status"]: g["tasks"] for g in groups}
        for task in tasks:
            bucket_key = task["status"]
            if bucket_key in bucket:
                bucket[bucket_key].append(task)
        return Response(groups)

    def _column_end_position(self, user, status):
        """Return the next available position (end of column, 1-based)."""
        return Task.objects.filter(user=user, status=status).count() + 1

    def _compact_column(self, user, status, exclude_id=None):
        """Re-number positions 1..n in a column after a removal."""
        qs = Task.objects.filter(user=user, status=status)
        if exclude_id is not None:
            qs = qs.exclude(pk=exclude_id)
        for new_pos, task in enumerate(
            qs.order_by(F("position").asc(nulls_last=True), "id"), start=1
        ):
            if task.position != new_pos:
                Task.objects.filter(pk=task.pk).update(position=new_pos)

    def perform_create(self, serializer):
        status_val = serializer.validated_data.get("status", Task.Status.PENDING)
        position = self._column_end_position(self.request.user, status_val)
        serializer.save(user=self.request.user, position=position)

    def perform_update(self, serializer):
        from datetime import timedelta

        previous = self.get_object()
        previous_status = previous.status
        previous_position = previous.position
        requested_status = serializer.validated_data.get("status", previous_status)

        # Extract position before saving to handle reorder logic manually
        requested_position = serializer.validated_data.pop("position", None)

        # Avoid transient unique(user,status,position) conflicts when status changes.
        if requested_status != previous_status:
            serializer.validated_data["position"] = None

        instance = serializer.save()

        # If status changed, compact old column and place task in new column.
        # If position was provided, insert at that slot; otherwise append to end.
        if instance.status != previous_status:
            with transaction.atomic():
                Task.objects.filter(pk=instance.pk).update(position=None)
                self._compact_column(instance.user, previous_status)

                target_qs = Task.objects.filter(
                    user=instance.user,
                    status=instance.status,
                ).exclude(pk=instance.pk)
                assigned_count = target_qs.filter(position__isnull=False).count()

                if requested_position is None:
                    new_pos = assigned_count + 1
                else:
                    new_pos = max(1, min(requested_position, assigned_count + 1))
                    affected = list(
                        target_qs.filter(
                            position__isnull=False,
                            position__gte=new_pos,
                        )
                        .order_by("-position")
                        .values_list("pk", "position")
                    )
                    for pk, pos in affected:
                        Task.objects.filter(pk=pk).update(position=pos + 1)

                Task.objects.filter(pk=instance.pk).update(position=new_pos)

        elif requested_position is not None and requested_position != previous_position:
            # Position changed within the same column — shift other tasks accordingly
            column_qs = Task.objects.filter(user=instance.user, status=instance.status)
            column_count = column_qs.count()
            new_position = max(1, min(requested_position, column_count))

            with transaction.atomic():
                # Temporarily clear position to avoid unique conflicts during shifts
                Task.objects.filter(pk=instance.pk).update(position=None)

                if previous_position is None:
                    affected = list(
                        column_qs.filter(position__gte=new_position)
                        .exclude(pk=instance.pk)
                        .order_by("-position")
                        .values_list("pk", "position")
                    )
                    for pk, pos in affected:
                        Task.objects.filter(pk=pk).update(position=pos + 1)
                elif new_position < previous_position:
                    affected = list(
                        column_qs.filter(
                            position__gte=new_position,
                            position__lt=previous_position,
                        )
                        .exclude(pk=instance.pk)
                        .order_by("-position")
                        .values_list("pk", "position")
                    )
                    for pk, pos in affected:
                        Task.objects.filter(pk=pk).update(position=pos + 1)
                else:
                    affected = list(
                        column_qs.filter(
                            position__gt=previous_position,
                            position__lte=new_position,
                        )
                        .exclude(pk=instance.pk)
                        .order_by("position")
                        .values_list("pk", "position")
                    )
                    for pk, pos in affected:
                        Task.objects.filter(pk=pk).update(position=pos - 1)

                Task.objects.filter(pk=instance.pk).update(position=new_position)

        # Keep serializer.instance in sync with DB updates done via queryset.update().
        instance.refresh_from_db()

        # Recurrence spawn on COMPLETED transition
        if (
            previous_status != Task.Status.COMPLETED
            and instance.status == Task.Status.COMPLETED
            and instance.recurrence_interval is not None
        ):
            spawn_pos = self._column_end_position(instance.user, Task.Status.PENDING)
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
                position=spawn_pos,
            )

    def perform_destroy(self, instance):
        status_val = instance.status
        user = instance.user
        instance.delete()
        self._compact_column(user, status_val)


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


# Fields allowed in the filter endpoint, with their type and supported operators.
# Only fields listed here can be filtered; operators are enforced per field type.
_COMPARISON_OPS = ["exact", "gt", "lt", "gte", "lte"]
_EXACT_ONLY = ["exact"]
_FILTERABLE_FIELDS = {
    # field name -> (orm_key, allowed_operators, cast_fn)
    "name": ("name__icontains", _EXACT_ONLY, str),
    "done": ("done", _EXACT_ONLY, None),  # cast handled specially
    "status": ("status", _EXACT_ONLY, str),
    "energy_level": ("energy_level", _COMPARISON_OPS, int),
    "date": ("date", _COMPARISON_OPS, str),
    "created_at": ("created_at", _COMPARISON_OPS, str),
    "updated_at": ("updated_at", _COMPARISON_OPS, str),
    "completed_at": ("completed_at", _COMPARISON_OPS, str),
    "tag": ("tag_id", _EXACT_ONLY, int),
    "recurrence_interval": ("recurrence_interval", _COMPARISON_OPS, int),
}


def _cast_bool(value):
    if value.lower() in ("true", "1", "yes"):
        return True
    if value.lower() in ("false", "0", "no"):
        return False
    raise ValueError


class TaskFilterView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Task.objects.filter(user=request.user)
        errors = {}

        for param, raw_value in request.query_params.lists():
            # Split param into field and optional operator (e.g. "energy_level__gte")
            parts = param.split("__", 1)
            field = parts[0]
            op = parts[1] if len(parts) == 2 else "exact"

            if field not in _FILTERABLE_FIELDS:
                errors[param] = [f"'{field}' is not a filterable field."]
                continue

            orm_base, allowed_ops, cast_fn = _FILTERABLE_FIELDS[field]
            if op not in allowed_ops:
                errors[param] = [
                    f"Operator '{op}' is not supported for '{field}'. "
                    f"Allowed: {', '.join(allowed_ops)}."
                ]
                continue

            # For multi-value params with exact op, use __in; otherwise last value wins
            values = raw_value  # list
            try:
                if field == "done":
                    cast_values = [_cast_bool(v) for v in values]
                else:
                    cast_values = [cast_fn(v) for v in values]
            except (ValueError, TypeError):
                errors[param] = [f"Invalid value for '{field}'."]
                continue

            if op == "exact" and field != "name":
                # For name we keep icontains; for everything else support multi-value via __in
                orm_key = orm_base + "__in" if len(cast_values) > 1 else orm_base
                filter_value = cast_values if len(cast_values) > 1 else cast_values[0]
            else:
                orm_key = orm_base if op == "exact" else orm_base + "__" + op
                filter_value = cast_values[-1]

            queryset = queryset.filter(**{orm_key: filter_value})

        if errors:
            raise ValidationError(errors)

        queryset = queryset.order_by("-created_at", "-id")
        serializer = TaskSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)
