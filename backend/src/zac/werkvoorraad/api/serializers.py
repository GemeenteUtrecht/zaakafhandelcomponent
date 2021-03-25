from django.urls import reverse
from django.utils.translation import gettext as _

from rest_framework import serializers
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.accounts.models import AccessRequest, User
from zac.activities.models import Activity
from zac.camunda.api.serializers import TaskSerializer
from zac.core.api.serializers import ZaakSerializer

from .data import AccessRequestGroup, ActivityGroup, TaskAndCase


class AccessRequestSerializer(APIModelSerializer):
    requester = serializers.SlugRelatedField(
        slug_field="username",
        queryset=User.objects.all(),
        help_text=_("Username of access requester/grantee"),
    )

    class Meta:
        model = AccessRequest
        fields = ("requester",)


class WorkStackAccessRequestsSerializer(APIModelSerializer):
    access_requests = AccessRequestSerializer(many=True)
    url = serializers.SerializerMethodField(
        help_text=_("This URL points to the case access requests."),
    )
    zaak = ZaakSerializer()

    class Meta:
        model = AccessRequestGroup
        fields = (
            "access_requests",
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
    url = serializers.SerializerMethodField(
        help_text=_("This URL points to the case adhoc activities."),
    )
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


class WorkStackTaskSerializer(APIModelSerializer):
    task = TaskSerializer()
    zaak = ZaakSerializer()

    class Meta:
        model = TaskAndCase
        fields = (
            "task",
            "zaak",
        )
