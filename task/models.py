from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator


class Task(models.Model):
    name = models.CharField(max_length=255)
    done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField()
    energy_level = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    def __str__(self) -> str:
        return self.name
