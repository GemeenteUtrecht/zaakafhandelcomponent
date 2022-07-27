from django.contrib import admin

from nested_admin import (
    NestedModelAdminMixin,
    NestedTabularInline,
    NestedTabularInlineMixin,
)
from ordered_model.admin import OrderedInlineModelAdminMixin, OrderedTabularInline

from .forms import CamundaStartProcessForm
from .models import (
    CamundaStartProcess,
    ProcessEigenschap,
    ProcessEigenschapChoice,
    ProcessInformatieObject,
    ProcessRol,
    ProcessRolChoice,
)


class ProcessInformatieObjectInlineAdmin(
    NestedTabularInlineMixin, OrderedTabularInline
):
    fields = (
        "informatieobjecttype_omschrijving",
        "label",
        "allow_multiple",
        "required",
        "move_up_down_links",
    )
    readonly_fields = ("move_up_down_links",)
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
        "order",
    ]


class ProcessRolChoiceInlineAdmin(NestedTabularInline):
    list_display = ("process_rol", "label", "value")
    autocomplete_fields = ("process_rol",)
    model = ProcessRolChoice
    extra = 0
    ordering = ["process_rol", "label"]


class ProcessRolInlineAdmin(NestedTabularInlineMixin, OrderedTabularInline):
    fields = (
        "roltype_omschrijving",
        "betrokkene_type",
        "label",
        "required",
        "move_up_down_links",
    )
    readonly_fields = ("move_up_down_links",)
    list_display = (
        "camunda_start_process",
        "roltype_omschrijving",
        "betrokkene_type",
    )
    list_filter = ("camunda_start_process",)
    search_fields = ("roltype_omschrijving",)
    autocomplete_fields = ("camunda_start_process",)
    inlines = [ProcessRolChoiceInlineAdmin]
    model = ProcessRol
    extra = 0
    ordering = [
        "order",
    ]


class ProcessEigenschapChoiceInlineAdmin(NestedTabularInline):
    list_display = ("process_eigenschap", "label", "value")
    autocomplete_fields = ("process_eigenschap",)
    model = ProcessEigenschapChoice
    extra = 0
    ordering = ["process_eigenschap", "label"]


class ProcessEigenschapInlineAdmin(NestedTabularInlineMixin, OrderedTabularInline):
    fields = ("eigenschapnaam", "label", "default", "required", "move_up_down_links")
    readonly_fields = ("move_up_down_links",)
    list_display = ("camunda_start_process", "eigenschapnaam")
    list_filter = ("camunda_start_process",)
    search_fields = ("eigenschapnaam",)
    autocomplete_fields = ("camunda_start_process",)
    inlines = [ProcessEigenschapChoiceInlineAdmin]
    model = ProcessEigenschap
    extra = 0
    ordering = [
        "order",
    ]


class CamundaStartProcessAdmin(
    OrderedInlineModelAdminMixin, NestedModelAdminMixin, admin.ModelAdmin
):
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
    inlines = [
        ProcessEigenschapInlineAdmin,
        ProcessRolInlineAdmin,
        ProcessInformatieObjectInlineAdmin,
    ]
    extra = 0


admin.site.register(CamundaStartProcess, CamundaStartProcessAdmin)
