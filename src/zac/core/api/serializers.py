from django.template.defaultfilters import filesizeformat
from django.urls import reverse

from rest_framework import serializers

from .utils import (
    CSMultipleChoiceField,
    ValidFieldChoices,
    get_informatieobjecttypen_for_zaak,
)


class InformatieObjectTypeSerializer(serializers.Serializer):
    url = serializers.URLField()
    omschrijving = serializers.CharField()


class AddDocumentSerializer(serializers.Serializer):
    informatieobjecttype = serializers.URLField(required=True)
    zaak = serializers.URLField(required=True)
    file = serializers.FileField(required=True, use_url=False)

    beschrijving = serializers.CharField(required=False)

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


class DocumentInfoSerializer(serializers.Serializer):
    document_type = serializers.CharField(source="informatieobjecttype.omschrijving")
    titel = serializers.CharField()
    vertrouwelijkheidaanduiding = serializers.CharField(
        source="get_vertrouwelijkheidaanduiding_display"
    )
    bestandsgrootte = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    def get_bestandsgrootte(self, obj):
        return filesizeformat(obj.bestandsomvang)

    def get_download_url(self, obj):
        path = reverse(
            "core:download-document",
            kwargs={
                "bronorganisatie": obj.bronorganisatie,
                "identificatie": obj.identificatie,
            },
        )
        return self.context["request"].build_absolute_uri(path)


class ExtraInfoUpSerializer(serializers.Serializer):
    doelbinding = serializers.CharField(
        allow_blank=False,
        required=True,
    )
    fields = CSMultipleChoiceField(
        choices=ValidFieldChoices.choices,
        required=True,
    )


class ExtraInfoSubjectSerializer(serializers.Serializer):
    geboortedatum = serializers.CharField()
    geboorteland = serializers.CharField()
    kinderen = serializers.ListField()
    verblijfplaats = serializers.DictField()
    partners = serializers.ListField()
