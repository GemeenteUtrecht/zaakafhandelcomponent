from django.contrib import admin
from django.forms import fields

from solo.admin import SingletonModelAdmin

from .models import CoreConfig, MetaObjectTypesConfig, WarningBanner


def get_objecttypes_choices():
    from zac.core.services import fetch_objecttypes

    try:
        ots = fetch_objecttypes()
    except Exception:
        return []
    return [(ot["url"], ot["name"]) for ot in ots]


@admin.register(CoreConfig)
class CoreConfigAdmin(SingletonModelAdmin):
    pass


@admin.register(MetaObjectTypesConfig)
class MetaObjectTypesConfigAdmin(SingletonModelAdmin):
    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj=obj, change=change, **kwargs)
        objecttype_fields = [
            "zaaktype_attribute_objecttype",
            "start_camunda_process_form_objecttype",
            "oudbehandelaren_objecttype",
            "checklisttype_objecttype",
            "checklist_objecttype",
            "meta_list_objecttype",
            "review_request_objecttype",
            "review_objecttype",
        ]
        for field in objecttype_fields:
            form.base_fields[field] = fields.ChoiceField(
                choices=get_objecttypes_choices(), required=False, initial=""
            )
        return form


@admin.register(WarningBanner)
class WarningLabelAdmin(SingletonModelAdmin):
    pass
