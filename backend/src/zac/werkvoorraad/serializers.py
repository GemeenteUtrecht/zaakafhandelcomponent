from django.core.validators import URLValidator
from django.urls import reverse
from django.utils.translation import gettext as _

from rest_framework import serializers
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.accounts.api.serializers import ZaakAccessSerializer
from zac.accounts.models import AccessRequest, User
from zac.activities.api.serializers import ActivitySerializer
from zac.activities.models import Activity
from zac.camunda.data import Task
from zac.core.api.serializers import ZaakSerializer
from zgw.models.zrc import Zaak

from .data import AccessRequestGroup, ActivityGroup


class AccessRequesterSerializer(APIModelSerializer):
    requester = serializers.SlugRelatedField(
        slug_field="username",
        queryset=User.objects.all(),
        help_text=_("Username of access requester/grantee"),
    )

    class Meta:
        model = AccessRequest
        fields = ("requester",)


class WorkStackAccessRequestsSerializer(APIModelSerializer):
    requesters = AccessRequesterSerializer(many=True)
    url = serializers.SerializerMethodField()
    zaak = ZaakSerializer()

    class Meta:
        model = AccessRequestGroup
        fields = (
            "requesters",
            "url",
            "zaak",
        )

    def get_url(self, obj) -> str:
        return reverse(
            "core:zaak-access-requests",
            kwargs={
                "bronorganisatie": obj.zaak.bronorganisatie,
                "identificatie": obj.zaak.identificatie,
            },
        )


class ActivityNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = ("name",)


class WorkStackAdhocActivitiesSerializer(APIModelSerializer):
    activities = ActivityNameSerializer(many=True)
    url = serializers.SerializerMethodField()
    zaak = ZaakSerializer()

    class Meta:
        model = ActivityGroup
        fields = (
            "activities",
            "url",
            "zaak",
        )

    def get_url(self, obj) -> str:
        return reverse(
            "core:zaak-activiteiten",
            kwargs={
                "bronorganisatie": obj.zaak.bronorganisatie,
                "identificatie": obj.zaak.identificatie,
            },
        )


class CaseTypeDescriptionSerializer(APIModelSerializer):
    class Meta:
        model = ZaakType
        fields = ("omschrijving",)


class WorkStackAssigneeCasesSerializer(APIModelSerializer):
    url = serializers.SerializerMethodField()
    zaaktype = CaseTypeDescriptionSerializer()

    class Meta:
        model = Zaak
        fields = (
            "einddatum",
            "einddatum_gepland",
            "identificatie",
            "startdatum",
            "url",
            "vertrouwelijkheidaanduiding",
            "zaaktype",
        )

    def get_url(self, obj) -> str:
        return reverse(
            "core:zaak-detail",
            kwargs={
                "bronorganisatie": obj.bronorganisatie,
                "identificatie": obj.identificatie,
            },
        )


class WorkStackUserTaskSerializer(APIModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = (
            "name",
            "url",
        )

    def get_url(self, obj) -> str:
        return reverse(
            "core:zaak-task",
            kwargs={
                "task_id": obj.id,
            },
        )
