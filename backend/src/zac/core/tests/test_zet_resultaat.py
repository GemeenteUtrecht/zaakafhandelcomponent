from unittest.mock import patch

import requests_mock
from django_camunda.models import CamundaConfig
from django_camunda.utils import serialize_variable, underscoreize
from freezegun import freeze_time
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory, APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.constants import APITypes, AuthTypes

from zac.activities.constants import ActivityStatuses
from zac.activities.tests.factories import ActivityFactory
from zac.camunda.data import Task
from zac.camunda.user_tasks import UserTaskData, get_context as _get_context
from zac.contrib.dowc.models import DowcConfig
from zac.contrib.objects.kownsl.data import ReviewRequest, Reviews
from zac.contrib.objects.kownsl.tests.factories import (
    review_request_factory,
    reviews_factory,
)
from zac.tests import ServiceFactory
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.mixins import FreezeTimeMixin
from zac.tests.utils import mock_resource_get, paginated_response

from ..camunda.zet_resultaat.serializers import ZetResultaatContextSerializer

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
DOCUMENTS_ROOT = "http://documents.nl/api/v1/"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"
PI_URL = "https://camunda.example.com/engine-rest/process-instance"
CAMUNDA_ROOT = "https://some.camunda.nl/"
CAMUNDA_API_PATH = "engine-rest/"
CAMUNDA_URL = f"{CAMUNDA_ROOT}{CAMUNDA_API_PATH}"
DOWC_API_ROOT = "https://dowc.nl/api/v1/"

# Taken from https://docs.camunda.org/manual/7.13/reference/rest/task/get/
TASK_DATA = {
    "id": "598347ee-62fc-46a2-913a-6e0788bc1b8c",
    "name": "aName",
    "assignee": None,
    "created": "2013-01-23T13:42:42.000+0200",
    "due": "2013-01-23T13:49:42.576+0200",
    "followUp": "2013-01-23T13:44:42.437+0200",
    "delegationState": "RESOLVED",
    "description": "aDescription",
    "executionId": "anExecution",
    "owner": "anOwner",
    "parentTaskId": None,
    "priority": 42,
    "processDefinitionId": "aProcDefId",
    "processInstanceId": "87a88170-8d5c-4dec-8ee2-972a0be1b564",
    "caseDefinitionId": "aCaseDefId",
    "caseInstanceId": "aCaseInstId",
    "caseExecutionId": "aCaseExecution",
    "taskDefinitionKey": "aTaskDefinitionKey",
    "suspended": False,
    "formKey": "",
    "tenantId": "aTenantId",
}

from zac.contrib.objects.checklists.tests.factories import (
    checklist_object_factory,
    checklist_type_object_factory,
)
from zac.core.tests.utils import ClearCachesMixin

CHECKLISTTYPE_OBJECT = checklist_type_object_factory()


def _get_task(**overrides):
    data = underscoreize({**TASK_DATA, **overrides})
    return factory(Task, data)


class GetZetResultaatContextSerializersTests(
    FreezeTimeMixin, ClearCachesMixin, APITestCase
):
    frozen_time = "2013-01-23T11:42:42Z"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        ServiceFactory.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        ServiceFactory.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        camunda_config = CamundaConfig.get_solo()
        camunda_config.root_url = CAMUNDA_ROOT
        camunda_config.rest_api_path = CAMUNDA_API_PATH
        camunda_config.save()

        cls.dowc_service = ServiceFactory.create(
            label="dowc",
            api_type=APITypes.orc,
            api_root=DOWC_API_ROOT,
            auth_type=AuthTypes.zgw,
            header_value="ApplicationToken some-token",
            header_key="Authorization",
            client_id="zac",
            secret="supersecret",
            user_id="zac",
        )

        dowc_config = DowcConfig.get_solo()
        dowc_config.service = cls.dowc_service
        dowc_config.save()

        catalogus_url = (
            f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=catalogus_url,
            domein=CHECKLISTTYPE_OBJECT["record"]["data"]["zaaktypeCatalogus"][0],
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=catalogus_url,
            url=f"{CATALOGI_ROOT}zaaktypen/6496bb11-499e-43d3-a6ca-2a43ed704952",
            identificatie=CHECKLISTTYPE_OBJECT["record"]["data"][
                "zaaktypeIdentificaties"
            ][0],
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=cls.zaaktype["url"],
        )
        cls.process_instance = {
            "id": "205eae6b-d26f-11ea-86dc-e22fafe5f405",
            "definitionId": "beleid_opstellen:8:c76c8200-c766-11ea-86dc-e22fafe5f405",
            "businessKey": "",
            "caseInstanceId": "",
            "suspended": False,
            "tenantId": "",
        }
        cls.process_definition = {
            "id": "beleid_opstellen:8:c76c8200-c766-11ea-86dc-e22fafe5f405",
            "key": "beleid_opstellen",
            "category": "http://bpmn.io/schema/bpmn",
            "description": None,
            "name": None,
            "version": 8,
            "resource": "accorderen.bpmn",
            "deployment_id": "c76a10fd-c766-11ea-86dc-e22fafe5f405",
            "diagram": None,
            "suspended": False,
            "tenant_id": None,
            "version_tag": None,
            "history_time_to_live": None,
            "startable_in_tasklist": True,
        }
        tasks = [_get_task(**{"formKey": "zac:zetResultaat"})]
        cls.get_top_level_process_instances_patcher = patch(
            "zac.core.camunda.zet_resultaat.context.get_camunda_user_tasks_for_zaak",
            return_value=tasks,
        )
        cls.resultaattype = generate_oas_component(
            "ztc", "schemas/ResultaatType", zaaktype=cls.zaaktype["url"]
        )

        with freeze_time("2013-01-23T11:42:42Z"):
            cls.activity = ActivityFactory.create(
                zaak=cls.zaak["url"], status=ActivityStatuses.on_going
            )

    def setUp(self):
        super().setUp()
        self.get_top_level_process_instances_patcher.start()
        self.addCleanup(self.get_top_level_process_instances_patcher.stop)

    @requests_mock.Mocker()
    def test_zet_resultaat_context_serializer(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, DOWC_API_ROOT, "dowc")
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{DOWC_API_ROOT}documenten/count?zaak={self.zaak['url']}",
            json={"count": 0},
        )
        task = _get_task(**{"formKey": "zac:zetResultaat"})
        m.get(
            f"{CAMUNDA_URL}task/{task.id}/variables/zaakUrl?deserializeValue=false",
            json=serialize_variable(self.zaak["url"]),
        )
        m.get(
            f"{CAMUNDA_URL}task/{task.id}/variables/resultaatTypeKeuzes?deserializeValue=false",
            json=serialize_variable([self.resultaattype["omschrijving"]]),
        )
        mock_resource_get(m, self.zaak)
        m.get(f"{ZAKEN_ROOT}zaakinformatieobjecten?zaak={self.zaak['url']}", json=[])
        m.post(f"{DOWC_API_ROOT}documenten/status", json=[])
        mock_resource_get(m, self.zaaktype)
        m.get(
            f"{CATALOGI_ROOT}resultaattypen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.resultaattype]),
        )
        checklist = checklist_object_factory()
        checklist["record"]["data"]["answers"][0]["answer"] = ""

        review_request = review_request_factory()
        rr = factory(ReviewRequest, review_request)

        # Avoid patching fetch_reviews and everything
        reviews = factory(Reviews, reviews_factory())
        rr.fetched_reviews = True

        with patch(
            "zac.core.camunda.zet_resultaat.context.get_all_review_requests_for_zaak",
            return_value=[rr],
        ) as patch_get_all_rr_4_zaak:
            with patch(
                "zac.core.camunda.zet_resultaat.context.get_reviews_for_zaak",
                return_value=[reviews],
            ) as patch_get_revs_4_zaak:
                with patch(
                    "zac.core.camunda.zet_resultaat.context.check_document_status",
                    return_value=[],
                ) as patch_check_document_status:
                    with patch(
                        "zac.contrib.objects.services.fetch_checklist_object",
                        return_value=checklist,
                    ):
                        with patch(
                            "zac.contrib.objects.services.fetch_checklisttype_object",
                            return_value=[CHECKLISTTYPE_OBJECT],
                        ):
                            task_data = UserTaskData(
                                task=task, context=_get_context(task)
                            )
        req_factory = APIRequestFactory()
        request = req_factory.get("/")

        serializer = ZetResultaatContextSerializer(
            instance=task_data,
            context={
                "request": Request(request),
            },
        )

        patch_check_document_status.assert_called_once()
        self.assertEqual(
            serializer.data["context"]["activiteiten"],
            [
                {
                    "created": "2013-01-23T11:42:42Z",
                    "created_by": None,
                    "document": "",
                    "events": [],
                    "group_assignee": None,
                    "id": self.activity.id,
                    "name": self.activity.name,
                    "remarks": self.activity.remarks,
                    "status": ActivityStatuses.on_going,
                    "user_assignee": None,
                    "zaak": self.zaak["url"],
                    "url": f"http://testserver/api/activities/activities/{self.activity.id}",
                }
            ],
        )
        self.assertEqual(
            serializer.data["context"]["checklist_vragen"],
            [
                {
                    "question": "Ja?",
                    "order": 1,
                    "choices": [{"name": "Ja", "value": "Ja"}],
                    "is_multiple_choice": True,
                },
            ],
        )
        self.assertEqual(
            serializer.data["context"]["taken"],
            [
                {
                    "id": TASK_DATA["id"],
                    "name": TASK_DATA["name"],
                    "created": "2013-01-23T11:42:42Z",
                    "has_form": False,
                    "assignee_type": "",
                    "can_cancel_task": False,
                    "assignee": None,
                    "form_key": "zac:zetResultaat",
                }
            ],
        )
        self.assertEqual(
            serializer.data["context"]["verzoeken"],
            [
                {
                    "id": "14aec7a0-06de-4b55-b839-a1c9a0415b46",
                    "review_type": "advice",
                    "completed": 1,
                    "num_assigned_users": 2,
                    "can_lock": False,
                    "locked": False,
                    "lock_reason": "",
                    "is_being_reconfigured": False,
                    "status": "pending",
                }
            ],
        )
        self.assertEqual(
            serializer.data["context"]["resultaattypen"],
            [
                {
                    "url": self.resultaattype["url"],
                    "omschrijving": self.resultaattype["omschrijving"],
                }
            ],
        )
        self.assertEqual(serializer.data["context"]["open_documenten"], [])
