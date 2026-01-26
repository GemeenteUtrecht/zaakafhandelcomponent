from django.contrib import admin

from .models import ChecklistLock


@admin.register(ChecklistLock)
class ChecklistLockAdmin(admin.ModelAdmin):
    list_display = (
        "zaak_identificatie",
        "user",
    )
    readonly_fields = ("zaak", "zaak_identificatie", "url")
    date_hierarchy = "created"
