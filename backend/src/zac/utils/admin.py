from urllib.parse import urlencode

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html, format_html_join

from django_camunda.admin import CamundaConfigAdmin
from django_camunda.models import CamundaConfig
from import_export.admin import ImportExportMixin
from zgw_consumers.admin import ServiceAdmin
from zgw_consumers.models import Service

from .resources import CamundaConfigResource, ServiceResource

admin.site.unregister(Service)
admin.site.unregister(CamundaConfig)


class ImportExportSoloMixin(ImportExportMixin):
    change_form_template = "utils/import_export_change_form.html"


@admin.register(Service)
class ServiceResourceAdmin(ImportExportMixin, ServiceAdmin):
    resource_class = ServiceResource


@admin.register(CamundaConfig)
class CamundaConfigResourceAdmin(ImportExportSoloMixin, CamundaConfigAdmin):
    resource_class = CamundaConfigResource


class RelatedLinksMixin:
    def display_related_as_list_of_links(self, obj, field_name):
        field = getattr(obj, field_name)
        model = field.model
        view_change = f"admin:{model._meta.app_label}_{model._meta.model_name}_change"
        return format_html_join(
            ", ",
            '<a href="{}">{}</a>',
            (
                (
                    reverse(
                        view_change,
                        args=[related_obj.id],
                    ),
                    str(related_obj),
                )
                for related_obj in field.all()
            ),
        )

    def display_related_as_count_with_link(self, obj, field_name):
        field = getattr(obj, field_name)
        model = field.model
        changelist_url = reverse(
            f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist"
        )
        field_name = (
            field.query_field_name
            if hasattr(field, "query_field_name")
            else field.field.name
        )
        query = {f"{field_name}__id__exact": obj.id}
        url = f"{changelist_url}?{urlencode(query)}"
        return format_html('<a href="{}">{}</a>', url, field.count())
