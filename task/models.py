import re

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone
from django.db import models
from django.conf import settings


def validate_hex_color(value):
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
        raise ValidationError("Enter a valid hex color (e.g. #A1B2C3).")


class TaskTag(models.Model):
    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="task_tags",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    color = models.CharField(max_length=7, validators=[validate_hex_color])

    def __str__(self) -> str:
        return self.name


class Task(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tasks",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255)
    done = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True, default=None)
    completed_at = models.DateTimeField(null=True, blank=True, default=None)
    description = models.TextField(blank=True)
    energy_level = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    tag = models.ForeignKey(
        TaskTag,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
    date = models.DateField(null=True, blank=True, default=None)
    recurrence_interval = models.PositiveIntegerField(
        null=True, blank=True, default=None
    )
    recurrence_origin = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        default=None,
        on_delete=models.SET_NULL,
        related_name="recurrences",
    )
    position = models.PositiveIntegerField(
        null=True,
        blank=True,
        default=None,
        validators=[MinValueValidator(1)],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "status", "position"],
                condition=models.Q(position__isnull=False),
                name="unique_task_position_per_user_status",
            )
        ]

    def save(self, *args, **kwargs):
        previous = None
        if self.pk is not None:
            previous = (
                Task.objects.filter(pk=self.pk).values("status", "completed_at").first()
            )
            self.updated_at = timezone.now()

        if self.status == Task.Status.COMPLETED:
            was_completed = previous and previous["status"] == Task.Status.COMPLETED
            if not was_completed:
                self.completed_at = timezone.now()
            elif self.completed_at is None and previous["completed_at"] is not None:
                self.completed_at = previous["completed_at"]
        else:
            self.completed_at = None

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name
