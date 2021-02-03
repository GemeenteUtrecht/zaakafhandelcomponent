from django.utils.translation import gettext_lazy as _

from rest_framework import serializers


class ZaakIdentificatieSerializer(serializers.Serializer):
    identificatie = serializers.CharField(
        required=True,
        label=_("zaak identification"),
        help_text=_(
            "Enter a (part) of the zaak identification you wish to "
            "find, case insensitive."
        ),
    )
