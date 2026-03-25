from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone
from django.db import models
from django.conf import settings


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
    description = models.TextField(blank=True)
    energy_level = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    def save(self, *args, **kwargs):
        if self.pk is not None:
            self.updated_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name
