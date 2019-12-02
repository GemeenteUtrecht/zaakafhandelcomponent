from django.contrib import admin

from django_camunda.admin import CamundaConfigAdmin
from django_camunda.models import CamundaConfig
from import_export.admin import ImportExportMixin
from nlx_url_rewriter.admin import URLRewriteAdmin
from nlx_url_rewriter.models import URLRewrite
from zgw_consumers.admin import ServiceAdmin
from zgw_consumers.models import Service

from .resources import CamundaConfigResource, ServiceResource, URLRewriteResource

admin.site.unregister(Service)
admin.site.unregister(URLRewrite)
admin.site.unregister(CamundaConfig)


class ImportExportSoloMixin(ImportExportMixin):
    change_form_template = "utils/import_export_change_form.html"


@admin.register(Service)
class ServiceResourceAdmin(ImportExportMixin, ServiceAdmin):
    resource_class = ServiceResource


@admin.register(URLRewrite)
class URLRewriteResourceAdmin(ImportExportMixin, URLRewriteAdmin):
    resource_class = URLRewriteResource


@admin.register(CamundaConfig)
class CamundaConfigResourceAdmin(ImportExportSoloMixin, CamundaConfigAdmin):
    resource_class = CamundaConfigResource
