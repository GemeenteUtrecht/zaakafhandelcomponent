from django.utils.translation import gettext as _

from rest_framework import serializers
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.accounts.models import AccessRequest, User
from zac.activities.models import Activity
from zac.camunda.api.serializers import TaskSerializer

from .data import AccessRequestGroup, ActivityGroup, TaskAndCase


class SummaryZaakDocumentSerializer(serializers.Serializer):
    url = serializers.URLField(help_text=_("URL of the zaak."))
    identificatie = serializers.CharField(help_text=_("Identificatie of the zaak."))
    bronorganisatie = serializers.CharField(help_text=_("Bronorganisatie of the zaak."))


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
    access_requests = AccessRequestSerializer(
        many=True, help_text=_("Access requests for requester to zaken.")
    )
    zaak = SummaryZaakDocumentSerializer(
        help_text=_("Zaak that access requests belong to.")
    )

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
    activities = ActivityNameSerializer(
        many=True, help_text=_("Names of the activities.")
    )
    zaak = SummaryZaakDocumentSerializer(help_text=_("Zaak that activity belongs to."))

    class Meta:
        model = ActivityGroup
        fields = (
            "activities",
            "zaak",
        )


class WorkStackTaskSerializer(APIModelSerializer):
    task = TaskSerializer(help_text=_("Camunda task for the user."))
    zaak = SummaryZaakDocumentSerializer(
        help_text=_("Zaak that camunda task belongs to.")
    )

    class Meta:
        model = TaskAndCase
        fields = (
            "task",
            "zaak",
        )
