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


class NullableJsonField(fields.JSONField):
    def get_attribute(self, instance):
        """
        Skip field if it's not included in the request.
        Nested fields are not supported
        """

        if self.source not in instance:
            raise fields.SkipField()

        return super().get_attribute(instance)
