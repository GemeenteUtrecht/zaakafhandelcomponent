from django.contrib import admin

from .models import UserTaskCallback


@admin.register(UserTaskCallback)
class UserTaskCallbackAdmin(admin.ModelAdmin):
    list_display = ("task_id", "callback_id", "callback_received")
    search_fields = ("task_id", "callback_id")
