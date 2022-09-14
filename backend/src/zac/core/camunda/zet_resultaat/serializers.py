from dataclasses import dataclass
from typing import Dict, List, Optional

from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from zgw_consumers.api_models.catalogi import ResultaatType
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.activities.api.serializers import ReadActivitySerializer
from zac.activities.models import Activity
from zac.api.context import get_zaak_context
from zac.camunda.api.serializers import TaskSerializer
from zac.camunda.data import Task
from zac.camunda.user_tasks import Context, usertask_context_serializer
from zac.contrib.kownsl.data import ReviewRequest
from zac.contrib.kownsl.serializers import ZaakRevReqSummarySerializer
from zac.core.api.serializers import ResultaatTypeSerializer
from zac.core.services import get_resultaattypen
from zac.objects.checklists.api.serializers import ChecklistQuestionSerializer
from zac.objects.checklists.data import ChecklistQuestion


@dataclass
class ZetResultaatContext(Context):
    activities: List[Optional[Activity]]
    checklist_questions: List[Optional[ChecklistQuestion]]
    review_requests: List[Optional[ReviewRequest]]
    tasks: List[Optional[Task]]
    result_types: List[Optional[ResultaatType]]


@usertask_context_serializer
class ZetResultaatContextSerializer(APIModelSerializer):
    activiteiten = ReadActivitySerializer(
        source="activities",
        many=True,
        allow_null=True,
        help_text=_("Open activities for ZAAK."),
    )
    checklist_vragen = ChecklistQuestionSerializer(
        source="checklist_questions",
        many=True,
        allow_null=True,
        help_text=_("Unanswered checklist questions for ZAAK."),
    )
    taken = TaskSerializer(
        source="tasks", many=True, allow_null=True, help_text=_("Open tasks for ZAAK.")
    )
    verzoeken = ZaakRevReqSummarySerializer(
        source="review_requests",
        many=True,
        allow_null=True,
        help_text=_("Open review requests for ZAAK."),
    )
    resultaattypen = ResultaatTypeSerializer(
        source="result_types",
        many=True,
        required=True,
        help_text=_("RESULTAATTYPEs for ZAAKTYPE of ZAAK."),
    )

    class Meta:
        model = ZetResultaatContext
        fields = (
            "activiteiten",
            "checklist_vragen",
            "taken",
            "verzoeken",
            "resultaattypen",
        )


#
# Write serializer
#


class ZetResultaatTaskSerializer(serializers.Serializer):
    """
    Serializes the `resultaat` for the user task.

    Requires ``task`` to be in serializer ``context``.
    """

    resultaat = serializers.CharField(
        required=True,
        help_text=_(
            "The RESULTAAT of the ZAAK. Required to be set before closing a ZAAK."
        ),
    )

    def validate_resultaat(self, resultaat) -> str:
        zaakcontext = get_zaak_context(self.context["task"], require_zaaktype=True)
        result_types = get_resultaattypen(zaakcontext.zaaktype)
        if resultaat not in [rt.omschrijving for rt in result_types]:
            raise serializers.ValidationError(
                _(
                    "RESULTAAT {resultaat} not found in RESULTAATTYPEN for ZAAKTYPE {zt}."
                ).format(resultaat=resultaat, zt=zaakcontext.zaaktype.omschrijving)
            )
        return resultaat

    def get_process_variables(self) -> Dict:
        """
        Sets `resultaat` variable in process.
        """
        return {"resultaat": self.validated_data["resultaat"]}

    def on_task_submission(self) -> None:
        """
        Asserts serializer is validated.
        """
        assert hasattr(self, "validated_data"), "Serializer is not validated."
