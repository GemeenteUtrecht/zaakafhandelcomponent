import logging
from typing import List, Tuple

from django import forms
from django.utils.translation import gettext_lazy as _

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
