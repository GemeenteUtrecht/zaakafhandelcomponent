from django.utils.translation import gettext as _

from rest_framework import serializers
from rest_framework_dataclasses.serializers import DataclassSerializer

from zac.accounts.models import AccessRequest, User
from zac.activities.models import Activity
from zac.api.polymorphism import PolymorphicSerializer
from zac.contrib.objects.checklists.data import ChecklistAnswer
from zac.contrib.objects.kownsl.api.serializers import (
    AdviceSerializer,
    ApprovalSerializer,
    OpenReviewSerializer,
)
from zac.contrib.objects.kownsl.constants import KownslTypes
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


class WorkStackAccessRequestsSerializer(DataclassSerializer):
    access_requests = AccessRequestSerializer(
        many=True, help_text=_("Access requests for requester to ZAAKen.")
    )
    zaak = SummaryZaakDocumentSerializer(
        help_text=_("ZAAK that access requests belong to.")
    )

    class Meta:
        dataclass = AccessRequestGroup
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


class WorkStackAdhocActivitiesSerializer(DataclassSerializer):
    activities = SummaryActivitySerializer(
        many=True, help_text=_("Summary of the activities.")
    )
    zaak = SummaryZaakDocumentSerializer(help_text=_("ZAAK that activity belongs to."))

    class Meta:
        dataclass = ActivityGroup
        fields = (
            "activities",
            "zaak",
        )


class WorkStackTaskSerializer(DataclassSerializer):
    task = serializers.CharField(
        help_text=_("Camunda task for the user."), source="task.name"
    )
    zaak = SummaryZaakDocumentSerializer(
        help_text=_("ZAAK that camunda task belongs to.")
    )

    class Meta:
        dataclass = TaskAndCase
        fields = (
            "task",
            "zaak",
        )


class SummaryChecklistAnswerSerializer(DataclassSerializer):
    class Meta:
        dataclass = ChecklistAnswer
        fields = ("question",)


class WorkStackChecklistAnswerSerializer(DataclassSerializer):
    checklist_questions = SummaryChecklistAnswerSerializer(
        many=True,
        help_text=_("Questions to be answered by assignee."),
        source="checklist_answers",
    )
    zaak = SummaryZaakDocumentSerializer(
        help_text=_("ZAAK that checklist questions belongs to.")
    )

    class Meta:
        dataclass = ChecklistAnswerGroup
        fields = (
            "checklist_questions",
            "zaak",
        )


class WorkStackAdviceSerializer(AdviceSerializer):
    class Meta:
        dataclass = AdviceSerializer.Meta.dataclass
        fields = ("created", "author", "advice", "group")
        # Note: created, author, and group are declared as fields in the parent class,
        # so we can't set extra_kwargs for them with DataclassSerializer
        extra_kwargs = {
            "advice": {"help_text": _("Advice given for review request.")},
        }


class WorkStackAdviceReviewsSerializer(serializers.Serializer):
    advices = WorkStackAdviceSerializer(many=True, source="get_reviews")


class WorkStackApprovalReviewsSerializer(serializers.Serializer):
    approvals = ApprovalSerializer(many=True, source="get_reviews")


class WorkStackReviewRequestSerializer(PolymorphicSerializer):
    serializer_mapping = {
        KownslTypes.advice: WorkStackAdviceReviewsSerializer,
        KownslTypes.approval: WorkStackApprovalReviewsSerializer,
    }
    discriminator_field = "review_type"
    id = serializers.UUIDField(help_text=_("The `id` of the review request."))
    review_type = serializers.ChoiceField(
        choices=KownslTypes.choices, help_text=_("The review type.")
    )
    open_reviews = OpenReviewSerializer(
        many=True, read_only=True, source="get_open_reviews"
    )
    is_being_reconfigured = serializers.BooleanField(
        help_text=_(
            "Boolean flag to indicate if review request is currently being reconfigured."
        ),
        required=True,
    )
    completed = serializers.IntegerField(
        label=_("completed requests"),
        help_text=_("The number of completed requests."),
        source="get_completed",
    )
    zaak = SummaryZaakDocumentSerializer(
        help_text=_("ZAAK that review request belongs to.")
    )


class WorkStackSummarySerializer(serializers.Serializer):
    user_tasks = serializers.IntegerField()
    group_tasks = serializers.IntegerField(default=0)
    zaken = serializers.IntegerField()
    reviews = serializers.IntegerField()
    user_activities = serializers.IntegerField()
    group_activities = serializers.IntegerField()
    access_requests = serializers.IntegerField()
