from django.utils.translation import gettext as _

from rest_framework import serializers
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.accounts.models import AccessRequest, User
from zac.activities.models import Activity
from zac.contrib.kownsl.serializers import ZaakRevReqDetailSerializer
from zac.contrib.objects.checklists.data import ChecklistAnswer
from zac.elasticsearch.drf_api.serializers import (
    StatusDocumentSerializer,
    ZaakTypeDocumentSerializer,
)

from .data import AccessRequestGroup, ActivityGroup, ChecklistAnswerGroup, TaskAndCase


class SummaryZaakDocumentSerializer(serializers.Serializer):
    url = serializers.URLField(
        help_text=_("URL reference of the ZAAK in Zaken API."),
    )
    identificatie = serializers.CharField(
        help_text=_("Unique identifier of ZAAK within `bronorganisatie`."),
    )
    bronorganisatie = serializers.CharField(
        help_text=_("The RSIN of the organisation that created the the ZAAK.")
    )
    status = StatusDocumentSerializer(help_text=_("STATUS of the ZAAK."))
    zaaktype = ZaakTypeDocumentSerializer(
        required=False, help_text=_("ZAAKTYPE of the ZAAK.")
    )
    omschrijving = serializers.CharField(
        required=False, help_text=_("Brief description of the ZAAK.")
    )
    deadline = serializers.DateTimeField(
        required=False,
        help_text=_(
            "Deadline of the ZAAK: returns `uiterlijke_einddatum_afdoening` if it's known. Otherwise it is calculated from `startdatum` and `doorlooptijd`."
        ),
    )


class AccessRequestSerializer(serializers.ModelSerializer):
    requester = serializers.SlugRelatedField(
        slug_field="username",
        queryset=User.objects.all(),
        help_text=_("`username` of access requester/grantee"),
    )

    class Meta:
        model = AccessRequest
        fields = (
            "id",
            "requester",
        )


class WorkStackAccessRequestsSerializer(APIModelSerializer):
    access_requests = AccessRequestSerializer(
        many=True, help_text=_("Access requests for requester to ZAAKen.")
    )
    zaak = SummaryZaakDocumentSerializer(
        help_text=_("ZAAK that access requests belong to.")
    )

    class Meta:
        model = AccessRequestGroup
        fields = (
            "access_requests",
            "zaak",
        )


class SummaryActivitySerializer(serializers.ModelSerializer):
    group_assignee = serializers.SlugRelatedField(
        slug_field="name",
        help_text=_("Name of the group assignee."),
        read_only=True,
    )
    user_assignee = serializers.SlugRelatedField(
        slug_field="username",
        help_text=_("Username of the user assignee."),
        read_only=True,
    )

    class Meta:
        model = Activity
        fields = ("name", "group_assignee", "user_assignee")


class WorkStackAdhocActivitiesSerializer(APIModelSerializer):
    activities = SummaryActivitySerializer(
        many=True, help_text=_("Summary of the activities.")
    )
    zaak = SummaryZaakDocumentSerializer(help_text=_("ZAAK that activity belongs to."))

    class Meta:
        model = ActivityGroup
        fields = (
            "activities",
            "zaak",
        )


class WorkStackTaskSerializer(APIModelSerializer):
    task = serializers.CharField(
        help_text=_("Camunda task for the user."), source="task.name"
    )
    zaak = SummaryZaakDocumentSerializer(
        help_text=_("ZAAK that camunda task belongs to.")
    )

    class Meta:
        model = TaskAndCase
        fields = (
            "task",
            "zaak",
        )


class SummaryChecklistAnswerSerializer(APIModelSerializer):
    class Meta:
        model = ChecklistAnswer
        fields = ("question",)


class WorkStackChecklistAnswerSerializer(APIModelSerializer):
    checklist_questions = SummaryChecklistAnswerSerializer(
        many=True,
        help_text=_("Questions to be answered by assignee."),
        source="checklist_answers",
    )
    zaak = SummaryZaakDocumentSerializer(
        help_text=_("ZAAK that checklist questions belongs to.")
    )

    class Meta:
        model = ChecklistAnswerGroup
        fields = (
            "checklist_questions",
            "zaak",
        )


class WorkStackReviewRequestSerializer(ZaakRevReqDetailSerializer):
    completed = serializers.IntegerField(
        label=_("completed requests"), help_text=_("The number of completed requests.")
    )
    zaak = SummaryZaakDocumentSerializer(
        help_text=_("ZAAK that review request belongs to."), source="for_zaak"
    )
