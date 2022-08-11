from django.contrib import admin
from django.forms import fields

from solo.admin import SingletonModelAdmin

from .models import CoreConfig


def get_objecttypes_choices():
    from zac.core.services import fetch_objecttypes

    try:
        ots = fetch_objecttypes()
    except Exception:
        return []
    return [(ot["url"], ot["name"]) for ot in ots]


@admin.register(CoreConfig)
class CoreConfigAdmin(SingletonModelAdmin):
    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj=obj, change=change, **kwargs)
        form.base_fields["zaaktype_attribute_object_type"] = fields.ChoiceField(
            choices=get_objecttypes_choices(), required=False, initial=""
        )
        return form
