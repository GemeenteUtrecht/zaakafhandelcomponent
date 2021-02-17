from django.utils.translation import gettext as _

from rest_framework import serializers
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.accounts.api.serializers import ZaakAccessSerializer
from zac.activities.api.serializers import ActivitySerializer
from zac.core.api.serializers import ZaakSerializer
from zgw.models.zrc import Zaak

from .data import AccessRequestGroup, ActivityGroup


class ZaakTypeOmschrijvingSerializer(APIModelSerializer):
    class Meta:
        model = ZaakType
        fields = ("omschrijving",)


class WorkStackAssigneeCasesSerializer(APIModelSerializer):
    zaaktype = ZaakTypeOmschrijvingSerializer()

    class Meta:
        model = Zaak
        fields = (
            "url",
            "identificatie",
            "bronorganisatie",
            "zaaktype",
            "startdatum",
            "einddatum",
            "einddatum_gepland",
            "vertrouwelijkheidaanduiding",
        )


class WorkStackAdhocActivitiesSerializer(APIModelSerializer):
    activities = ActivitySerializer(many=True)
    zaak = ZaakSerializer()
    zaak_url = serializers.URLField()

    class Meta:
        model = ActivityGroup
        fields = (
            "activities",
            "zaak",
            "zaak_url",
        )


class WorkStackAccessRequestsSerializer(APIModelSerializer):
    requesters = ZaakAccessSerializer(many=True)
    zaak = ZaakSerializer()
    zaak_url = serializers.URLField()

    class Meta:
        model = AccessRequestGroup
        fields = (
            "requesters",
            "zaak",
            "zaak_url",
        )
