from django.contrib import admin

from .models import CamundaStartProcessForm


# Register your models here.
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
