from django.contrib import admin

from nested_admin import NestedModelAdmin, NestedStackedInline, NestedTabularInline

from .forms import CamundaStartProcessForm
from .models import (
    CamundaStartProcess,
    ProcessEigenschap,
    ProcessEigenschapChoice,
    ProcessInformatieObject,
    ProcessRol,
)


class ProcessInformatieObjectAdmin(NestedStackedInline):
    list_display = (
        "camunda_start_process",
        "informatieobjecttype_omschrijving",
    )
    list_filter = ("camunda_start_process",)
    search_fields = ("informatieobjecttype_omschrijving",)
    autocomplete_fields = ("camunda_start_process",)
    model = ProcessInformatieObject
    extra = 0
    ordering = [
        "camunda_start_process",
        "informatieobjecttype_omschrijving",
    ]


class ProcessRolAdmin(NestedStackedInline):
    list_display = (
        "camunda_start_process",
        "roltype_omschrijving",
        "betrokkene_type",
    )
    list_filter = ("camunda_start_process",)
    search_fields = ("roltype_omschrijving",)
    autocomplete_fields = ("camunda_start_process",)
    model = ProcessRol
    extra = 0
    ordering = [
        "camunda_start_process",
        "roltype_omschrijving",
        "betrokkene_type",
    ]


class ProcessEigenschapChoiceAdmin(NestedTabularInline):
    list_display = ("process_eigenschap", "label", "value")
    autocomplete_fields = ("process_eigenschap",)
    model = ProcessEigenschapChoice
    extra = 0
    ordering = ["process_eigenschap", "label"]


class ProcessEigenschapAdmin(NestedStackedInline):
    list_display = ("camunda_start_process", "eigenschapnaam")
    list_filter = ("camunda_start_process",)
    search_fields = ("eigenschapnaam",)
    autocomplete_fields = ("camunda_start_process",)
    inlines = [ProcessEigenschapChoiceAdmin]
    model = ProcessEigenschap
    extra = 0
    ordering = ["camunda_start_process", "eigenschapnaam"]


class CamundaStartProcessAdmin(NestedModelAdmin):
    list_display = (
        "process_definition_key",
        "zaaktype_identificatie",
    )
    list_filter = ("process_definition_key",)
    search_fields = (
        "process_definition_key",
        "zaaktype_identificatie",
    )
    form = CamundaStartProcessForm
    inlines = [ProcessEigenschapAdmin, ProcessRolAdmin, ProcessInformatieObjectAdmin]
    extra = 0


admin.site.register(CamundaStartProcess, CamundaStartProcessAdmin)
