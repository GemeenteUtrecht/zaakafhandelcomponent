from dataclasses import dataclass
from typing import Dict, List, Optional

from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from zgw_consumers.api_models.catalogi import ResultaatType
from zgw_consumers.api_models.documenten import Document

from zac.activities.api.serializers import ReadActivitySerializer
from zac.activities.models import Activity
from zac.api.context import get_zaak_context
from zac.camunda.api.serializers import TaskSerializer
from zac.camunda.data import Task
from zac.camunda.user_tasks import Context, usertask_context_serializer
from zac.contrib.dowc.data import OpenDowc
from zac.contrib.objects.checklists.api.serializers import ChecklistQuestionSerializer
from zac.contrib.objects.checklists.data import ChecklistQuestion
from zac.contrib.objects.kownsl.api.serializers import ZaakRevReqSummarySerializer
from zac.contrib.objects.kownsl.data import ReviewRequest
from zac.core.api.serializers import ResultaatTypeSerializer
from zac.core.cache import invalidate_zaak_cache
from zac.core.services import get_resultaattypen
from zac.tests.compat import APIModelSerializer


@dataclass
class ZetResultaatContext(Context):
    activities: List[Optional[Activity]]
    checklist_questions: List[Optional[ChecklistQuestion]]
    review_requests: List[Optional[ReviewRequest]]
    tasks: List[Optional[Task]]
    result_types: List[Optional[ResultaatType]]
    open_documenten: List[Optional[Document]]


class OpenDocumentSerializer(APIModelSerializer):
    url = serializers.CharField(
        source="document",
        help_text=_("Unversioned URL-reference to INFORMATIEOBJECT in DRC API."),
    )
    locked_by = serializers.EmailField(
        help_text=_("Email of user that locked document.")
    )

    class Meta:
        model = OpenDowc
        fields = ("url", "locked_by")


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
    open_documenten = OpenDocumentSerializer(
        help_text=_(
            "URL-references of INFORMATIEOBJECTs of DRC API in DOWC API that are currently being edited."
        ),
        many=True,
        required=True,
    )

    class Meta:
        model = ZetResultaatContext
        fields = (
            "activiteiten",
            "checklist_vragen",
            "taken",
            "verzoeken",
            "resultaattypen",
            "open_documenten",
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

    def _get_zaak_context(self):
        if not hasattr(self, "_zaak_context"):
            self._zaak_context = get_zaak_context(
                self.context["task"], require_zaaktype=True
            )
        return self._zaak_context

    def validate_resultaat(self, resultaat) -> str:
        zaakcontext = self._get_zaak_context()
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

        Closes all "open" documents in DoWC.
        Locks all review requests.
        Ends all activities.
        Unassigns all unanswered checklist questions.
        Process instance is gracefully ended.

        """
        assert hasattr(self, "validated_data"), "Serializer is not validated."
        zaakcontext = self._get_zaak_context()

        # Clear all related cache.
        invalidate_zaak_cache(zaakcontext.zaak)
