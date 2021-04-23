from rest_framework import serializers

from ..models import Report


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = (
            "id",
            "name",
        )


class ReportDownloadSerializer(serializers.Serializer):
    identificatie = serializers.CharField()
    omschrijving = serializers.CharField()
    startdatum = serializers.DateField()
    status = serializers.CharField()
    zaaktype_omschrijving = serializers.CharField()
    eigenschappen = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField()), allow_empty=True
    )
