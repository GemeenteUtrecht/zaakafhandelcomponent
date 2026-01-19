import json

from django_camunda.models import CamundaConfig
from import_export import resources, widgets
from zgw_consumers.models import Service


class JSONWidget(widgets.Widget):
    """Convert data into JSON for serialization."""

    def clean(self, value, row=None, *args, **kwargs):
        return json.loads(value)

    def render(self, value, obj=None):
        if value is None:
            return ""
        return json.dumps(value)


class JSONResourceMixin(object):
    """Override ModelResource to provide JSON field support."""

    @classmethod
    def widget_from_django_field(cls, f, default=widgets.Widget):
        if f.get_internal_type() in ("JSONField",):
            return JSONWidget
        else:
            return super().widget_from_django_field(f)


class SoloModelResource(resources.ModelResource):
    def export(self, queryset=None, *args, **kwargs):
        model = self._meta.model
        model.get_solo()
        return super().export(queryset, *args, **kwargs)


class ServiceResource(JSONResourceMixin, resources.ModelResource):
    class Meta:
        model = Service


class CamundaConfigResource(SoloModelResource):
    class Meta:
        model = CamundaConfig
