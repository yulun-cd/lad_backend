from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class DailyLog(models.Model):
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
