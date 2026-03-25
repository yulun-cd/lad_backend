from datetime import date as date_type

from django.core.validators import MaxValueValidator, MinValueValidator
from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class DailyLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="daily_logs",
        null=True,
        blank=True,
    )
    date = models.DateField()
    overall = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    energy = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    emotion = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    productivity = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    description = models.TextField(blank=True)
    updated_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta:
        unique_together = [("user", "date")]

    def clean(self):
        if self.date > date_type.today():
            raise ValidationError({"date": "Date cannot be in the future."})

    def save(self, *args, **kwargs):
        self.clean()
        if self.pk is not None:
            self.updated_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"DailyLog {self.date.isoformat()}"
