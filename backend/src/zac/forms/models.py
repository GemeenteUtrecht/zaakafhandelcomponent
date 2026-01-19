from django.db import models
from django.utils.translation import gettext_lazy as _

from solo.models import SingletonModel
from zgw_consumers.constants import APITypes


class FormsConfig(SingletonModel):
    """
    A singleton model to configure the required credentials to communicate with the an Open Forms implementation.

    Not currently used.
    """

    forms_service = models.ForeignKey(
        "zgw_consumers.Service",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        limit_choices_to={"api_type": APITypes.orc},
        help_text=_("Select the service definition where Open Forms is hosted."),
    )

    class Meta:
        verbose_name = "formulierenconfiguratie"

    def __str__(self):
        return "Formulierenconfiguratie"
