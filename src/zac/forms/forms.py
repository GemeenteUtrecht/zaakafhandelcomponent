import logging
from copy import copy
from typing import List, Tuple

from django import forms
from django.core.validators import MaxLengthValidator, RegexValidator
from django.utils.translation import gettext_lazy as _

from zac.contrib.kadaster.forms import PandSelectieField

from .client import OpenFormsClient

logger = logging.getLogger(__name__)


def get_form_choices() -> List[Tuple[str, str]]:
    logger.info("Calling Open Forms API to get form definitions...")
    client = OpenFormsClient()
    definitions = client.get_forms()
    return [(definition["id"], definition["name"]) for definition in definitions]


class SelectFormForm(forms.Form):
    """
    Query the Open Forms installation and present a list of forms that can be started.
    """

    form_id = forms.ChoiceField(label=_("Formulier"), choices=get_form_choices)


def generate_form_class(form_id: int):
    Form = copy(forms.BaseForm)
    Form.base_fields = {}

    client = OpenFormsClient()
    fields = client.get_form_fields(form_id)
    for field in fields:
        name, form_field = _get_field(field)
        Form.base_fields[name] = form_field
    return Form


KNOWN_FIELD_TYPES = {
    "openforms.contrib.kadaster.field_types.PandSelectie": PandSelectieField,
    "openforms.contrib.zgw.field_types.DocumentUpload": forms.FileField,
}


def _get_field(field_definition: dict) -> Tuple[str, forms.Field]:
    name = field_definition["name"]

    # figure out the form field class
    # core datatypes are just wrappers around the django form fields
    field_type = field_definition["datatype"]

    if field_type.startswith("openforms.formbuilder.field_types."):
        _field_class = field_type.replace("openforms.formbuilder.field_types.", "")
        try:
            field_class = getattr(forms, _field_class)
        except AttributeError:
            logger.warning(
                f"Could not resolve {field_definition['datatype']} to a form field class"
            )
            field_class = forms.CharField
    elif field_type in KNOWN_FIELD_TYPES:
        field_class = KNOWN_FIELD_TYPES[field_type]
    else:
        # TODO: known 'special' contrib cases
        logger.warning(
            f"Could not resolve {field_definition['datatype']} to a form field class"
        )
        field_class = forms.CharField

    field_kwargs = {
        "label": field_definition["label"],
        "required": field_definition["required"],
        "initial": field_definition["default"] or None,
        "help_text": field_definition["help_text"],
        "validators": [],
    }
    if field_definition["max_length"]:
        max_len_validator = MaxLengthValidator(field_definition["max_length"])
        field_kwargs["validators"].append(max_len_validator)

    if field_definition["validation_rule_regex"]:
        re_validator = RegexValidator(field_definition["validation_rule_regex"])
        field_kwargs["validators"].append(re_validator)

    if field_definition["hidden"]:
        field_kwargs["widget"] = forms.HiddenInput
    elif field_definition["widget"]:
        widget = getattr(forms, field_definition["widget"])
        widget_kwargs = {"attrs": {"placeholder": field_definition["example_value"]}}
        field_kwargs["widget"] = widget(**widget_kwargs)

    field = field_class(**field_kwargs)
    return name, field
