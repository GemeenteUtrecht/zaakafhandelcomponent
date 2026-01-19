from django.utils.translation import gettext_lazy as _

from rest_framework.fields import ListField, URLField

from zac.core.api.validators import ZaakEigenschappenValidator


class SelectZaakEigenschappenKownslField(ListField):
    """
    Specialized field for kownsl where ZAAKEIGENSCHAP selection takes place.
    Requires a `get_zaak_from_context` method on the serializer.

    """

    child = URLField()

    default_validators = [
        ZaakEigenschappenValidator(),
    ]

    def __init__(self, *args, **kwargs):
        kwargs.setdefault(
            "label", _("Select the relevant ZAAKEIGENSCHAPs for the advice/approval.")
        )
        kwargs.setdefault(
            "help_text",
            _(
                "These are the ZAAKEIGENSCHAPs that belong to the ZAAK. Please select te relevant ZAAKEIGENSCHAPs."
            ),
        )
        super().__init__(*args, **kwargs)
