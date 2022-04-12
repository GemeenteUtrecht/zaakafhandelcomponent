from django.contrib import admin

from .models import KillableTask


@admin.register(KillableTask)
class KillableTaskAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
