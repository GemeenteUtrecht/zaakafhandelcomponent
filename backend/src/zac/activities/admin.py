from django.contrib import admin

from .models import Activity, Event


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("name", "zaak", "status")
    list_filter = ("status",)
    search_fields = ("zaak", "name")
    date_hierarchy = "created"


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("__str__",)
    list_filter = ("activity",)
    search_fields = ("activity__zaak",)
    date_hierarchy = "created"
    autocomplete_fields = ("activity",)
