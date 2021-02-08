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


class SearchZaaktypeSerializer(serializers.Serializer):
    omschrijving = serializers.CharField(
        help_text=_(
            "Description of ZAAKTYPE, used as an aggregator of different versions of ZAAKTYPE"
        )
    )
    catalogus = serializers.URLField(help_text=_("Url reference of related CATALOGUS"))


class SearchSerializer(serializers.Serializer):
    identificatie = serializers.CharField(
        required=False,
        help_text=_("Unique identifier of ZAAK within `bronorganisatie`"),
    )
    zaaktype = SearchZaaktypeSerializer(
        required=False, help_text=_("Properties to identify ZAAKTYPEn")
    )
    omschrijving = serializers.CharField(
        required=False, help_text=_("Brief description of ZAAK")
    )
    eigenschappen = serializers.JSONField(
        required=False,
        help_text=_(
            "ZAAK-EIGENSCHAPpen in format `<property name>:{'value': <property value>}`"
        ),
    )

    def validate_eigenschappen(self, data):
        validated_data = dict()
        for name, value in data.items():
            if not isinstance(value, dict):
                raise serializers.ValidationError(
                    "'Eigenschappen' field values should be JSON objects"
                )
            if "value" not in value:
                raise serializers.ValidationError(
                    "'Eigenschappen' fields should include 'value' attribute"
                )
            validated_data[name] = value["value"]
        return validated_data
