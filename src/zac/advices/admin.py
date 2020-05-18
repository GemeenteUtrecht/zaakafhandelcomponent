from django.contrib import admin

from .models import Advice


@admin.register(Advice)
class AdviceAdmin(admin.ModelAdmin):
    list_display = ("created", "object_url", "object_type", "accord")
    list_filter = ("object_type",)
    search_fields = ("object_url",)
    date_hierarchy = "created"
