from django.core.validators import MaxValueValidator, MinValueValidator
from django.conf import settings
from django.db import models


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

    def __str__(self) -> str:
        return f"DailyLog {self.date.isoformat()}"
