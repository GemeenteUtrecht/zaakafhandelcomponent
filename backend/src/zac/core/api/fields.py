from django.utils.translation import gettext_lazy as _

from rest_framework import fields

from .validators import ZaakDocumentsValidator


class SelectDocumentsField(fields.ListField):
    child = fields.URLField()

    default_validators = [
        ZaakDocumentsValidator(),
    ]

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label", _("Selecteer de relevante documenten"))
        kwargs.setdefault(
            "help_text",
            _(
                "Dit zijn de documenten die bij de zaak horen. Selecteer de relevante "
                "documenten."
            ),
        )
        super().__init__(*args, **kwargs)
