from django.utils.translation import gettext as _

from rest_framework import serializers
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.accounts.api.serializers import ZaakAccessSerializer
from zac.activities.api.serializers import ActivitySerializer
from zac.core.api.serializers import ZaakSerializer

from .data import AccessRequestGroup, ActivityGroup


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
