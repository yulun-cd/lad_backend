from django.contrib import admin

from task.models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "user",
        "status",
        "done",
        "energy_level",
        "created_at",
    )
    list_filter = ("status", "done", "energy_level")
    search_fields = ("name", "description")


# Register your models here.
