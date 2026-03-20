from django.contrib import admin
from daily_log.models import DailyLog


@admin.register(DailyLog)
class DailyLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "date",
        "user",
        "overall",
        "energy",
        "emotion",
        "productivity",
    )
    list_filter = ("date", "overall", "energy", "emotion", "productivity")
    search_fields = ("description",)
