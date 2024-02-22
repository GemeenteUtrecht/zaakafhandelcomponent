from dataclasses import dataclass
from typing import Dict, List, Optional

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from djangorestframework_camel_case.settings import api_settings
from djangorestframework_camel_case.util import camelize
from rest_framework import serializers
from zgw_consumers.api_models.catalogi import ResultaatType
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.concurrent import parallel
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.activities.api.serializers import ReadActivitySerializer
from zac.activities.constants import ActivityStatuses
from zac.activities.models import Activity
from zac.api.context import get_zaak_context
from zac.camunda.api.serializers import TaskSerializer
from zac.camunda.data import Task
from zac.camunda.user_tasks import Context, usertask_context_serializer
from zac.contrib.dowc.api import check_document_status, patch_and_destroy_doc
from zac.contrib.dowc.data import OpenDowc
from zac.contrib.objects.checklists.api.serializers import ChecklistQuestionSerializer
from zac.contrib.objects.checklists.data import ChecklistQuestion
from zac.contrib.objects.kownsl.api.serializers import ZaakRevReqSummarySerializer
from zac.contrib.objects.kownsl.data import ReviewRequest
from zac.contrib.objects.services import (
    fetch_checklist_object,
    get_all_review_requests_for_zaak,
    get_reviews_for_zaak,
    lock_review_request,
)
from zac.core.api.serializers import ResultaatTypeSerializer
from zac.core.cache import invalidate_zaak_cache
from zac.core.services import get_resultaattypen, update_object_record_data


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
    Closes any open documents.

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

    def _close_documents(self):
        zaakcontext = self._get_zaak_context()
        open_documents = check_document_status(zaak=zaakcontext.zaak.url)

        def _patch_and_destroy_doc(uuid: str):
            return patch_and_destroy_doc(uuid, force=True)

        with parallel(max_workers=settings.MAX_WORKERS) as executor:
            list(
                executor.map(
                    _patch_and_destroy_doc, [str(doc.uuid) for doc in open_documents]
                )
            )

    def _lock_review_requests(self):
        zaakcontext = self._get_zaak_context()
        review_requests = get_all_review_requests_for_zaak(zaakcontext.zaak)

        def _lock_review_requests(uuid: str):
            return lock_review_request(
                uuid, f"Zaak is {self.validated_data['resultaat']}."
            )

        with parallel(max_workers=settings.MAX_WORKERS) as executor:
            list(
                executor.map(
                    _lock_review_requests, [str(rr.id) for rr in review_requests]
                )
            )

    def _close_activities(self):
        zaakcontext = self._get_zaak_context()
        activities = Activity.objects.prefetch_related("events").filter(
            zaak=zaakcontext.zaak.url, status=ActivityStatuses.on_going
        )
        for activity in activities:
            activity.user_assignee = None
            activity.group_assignee = None
            activity.status = ActivityStatuses.finished
            activity.save()

    def _lock_checklist(self):
        zaakcontext = self._get_zaak_context()
        checklist = fetch_checklist_object(zaakcontext.zaak)
        if checklist:
            updated = False
            for answer in checklist["record"]["data"]["answers"]:
                if not answer["answer"] and (
                    answer.get("userAssignee") or answer.get("groupAssignee")
                ):
                    updated = True
                    answer["userAssignee"] = ""
                    answer["groupAssignee"] = ""
            checklist["record"]["data"]["lockedBy"] = (
                f"{self.context['request'].user}" or "service-account"
            )

            if updated:
                update_object_record_data(
                    object=checklist,
                    data=camelize(
                        checklist["record"]["data"], **api_settings.JSON_UNDERSCOREIZE
                    ),
                    user=self.context["request"].user,
                )

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

        self._close_documents()
        self._lock_review_requests()
        self._close_activities()
        self._lock_checklist()

        # Clear all related cache.
        invalidate_zaak_cache(zaakcontext.zaak)
