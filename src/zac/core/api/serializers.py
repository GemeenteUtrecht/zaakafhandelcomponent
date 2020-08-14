from rest_framework import serializers

from .utils import get_informatieobjecttypen_for_zaak


class InformatieObjectTypeSerializer(serializers.Serializer):
    url = serializers.URLField()
    omschrijving = serializers.CharField()


class AddDocumentSerializer(serializers.Serializer):
    informatieobjecttype = serializers.URLField(required=True)
    zaak = serializers.URLField(required=True)
    file = serializers.FileField(required=True, use_url=False)

    def validate(self, data):
        zaak_url = data.get("zaak")
        informatieobjecttype_url = data.get("informatieobjecttype")

        if zaak_url and informatieobjecttype_url:
            informatieobjecttypen = get_informatieobjecttypen_for_zaak(zaak_url)
            present = any(
                iot
                for iot in informatieobjecttypen
                if iot.url == informatieobjecttype_url
            )
            if not present:
                raise serializers.ValidationError(
                    "Invalid informatieobjecttype URL given."
                )

        return data


class AddDocumentResponseSerializer(serializers.Serializer):
    document = serializers.URLField(source="url")
