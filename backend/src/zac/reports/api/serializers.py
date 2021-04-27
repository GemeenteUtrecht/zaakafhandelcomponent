from rest_framework import serializers
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.core.api.serializers import ZaakEigenschapSerializer, ZaakStatusSerializer
from zgw.models.zrc import Zaak

from ..models import Report


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = (
            "id",
            "name",
        )


class ReportDownloadSerializer(APIModelSerializer):
    status = ZaakStatusSerializer(allow_null=True)
    zaaktype_omschrijving = serializers.CharField(source="zaaktype.omschrijving")
    eigenschappen = ZaakEigenschapSerializer(many=True, allow_null=True)

    class Meta:
        model = Zaak
        fields = (
            "identificatie",
            "omschrijving",
            "startdatum",
            "status",
            "zaaktype_omschrijving",
            "eigenschappen",
        )
