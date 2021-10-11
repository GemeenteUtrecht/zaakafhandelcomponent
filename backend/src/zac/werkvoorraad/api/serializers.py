from django.utils.translation import gettext as _

from rest_framework import serializers
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.accounts.models import AccessRequest, User
from zac.activities.models import Activity
from zac.camunda.api.serializers import TaskSerializer
from zac.elasticsearch.drf_api.serializers import ZaakDocumentSerializer

from .data import AccessRequestGroup, ActivityGroup, TaskAndCase


class AccessRequestSerializer(serializers.ModelSerializer):
    requester = serializers.SlugRelatedField(
        slug_field="username",
        queryset=User.objects.all(),
        help_text=_("Username of access requester/grantee"),
    )

    class Meta:
        model = AccessRequest
        fields = (
            "id",
            "requester",
        )


class WorkStackAccessRequestsSerializer(APIModelSerializer):
    access_requests = AccessRequestSerializer(many=True)
    zaak = ZaakDocumentSerializer()

    class Meta:
        model = AccessRequestGroup
        fields = (
            "access_requests",
            "zaak",
        )


class ActivityNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = ("name",)


class WorkStackAdhocActivitiesSerializer(APIModelSerializer):
    activities = ActivityNameSerializer(many=True)
    zaak = ZaakDocumentSerializer()

    class Meta:
        model = ActivityGroup
        fields = (
            "activities",
            "zaak",
        )


class WorkStackTaskSerializer(APIModelSerializer):
    task = TaskSerializer()
    zaak = ZaakDocumentSerializer()

    class Meta:
        model = TaskAndCase
        fields = (
            "task",
            "zaak",
        )
