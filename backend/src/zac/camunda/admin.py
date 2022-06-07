from django.contrib import admin

from .models import CamundaStartProcessForm, KillableTask


@admin.register(KillableTask)
class KillableTaskAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(CamundaStartProcessForm)
class CamundaStartProcessFormAdmin(admin.ModelAdmin):
    list_display = (
        "process_definition_key",
        "zaaktype_identificatie",
    )
    search_fields = (
        "process_definition_key",
        "zaaktype_identificatie",
    )
