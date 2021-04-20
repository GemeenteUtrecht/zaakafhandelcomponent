from rest_framework import serializers
from zgw_consumers.drf.serializers import APIModelSerializer

from ..models import Report
from .data import ReportRow


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = (
            "id",
            "name",
        )


class ReportDownloadSerializer(APIModelSerializer):
    class Meta:
        model = ReportRow
        fields = (
            "eigenschappen",
            "identificatie",
            "omschrijving",
            "startdatum",
            "status",
            "zaaktype_omschrijving",
        )
