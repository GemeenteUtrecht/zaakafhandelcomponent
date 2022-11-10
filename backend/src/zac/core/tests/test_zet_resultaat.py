from unittest.mock import patch

import requests_mock
from django_camunda.models import CamundaConfig
from django_camunda.utils import serialize_variable, underscoreize
from freezegun import freeze_time
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory, APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.activities.constants import ActivityStatuses
from zac.activities.tests.factories import ActivityFactory
from zac.camunda.data import ProcessInstance, Task
from zac.camunda.user_tasks import UserTaskData, get_context as _get_context
from zac.contrib.kownsl.models import KownslConfig
from zac.contrib.kownsl.tests.utils import REVIEW_REQUEST
from zac.tests.utils import mock_resource_get, paginated_response

from ..camunda.zet_resultaat.serializers import ZetResultaatContextSerializer

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
DOCUMENTS_ROOT = "http://documents.nl/api/v1/"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"
PI_URL = "https://camunda.example.com/engine-rest/process-instance"
CAMUNDA_ROOT = "https://some.camunda.nl/"
CAMUNDA_API_PATH = "engine-rest/"
CAMUNDA_URL = f"{CAMUNDA_ROOT}{CAMUNDA_API_PATH}"
KOWNSL_ROOT = "https://kownsl.nl/"

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

from zac.objects.checklists.tests.utils import CHECKLIST_OBJECT, CHECKLISTTYPE_OBJECT


def _get_task(**overrides):
    data = underscoreize({**TASK_DATA, **overrides})
    return factory(Task, data)


@freeze_time("2013-01-23T11:42:42Z")
class GetZetResultaatContextSerializersTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        camunda_config = CamundaConfig.get_solo()
        camunda_config.root_url = CAMUNDA_ROOT
        camunda_config.rest_api_path = CAMUNDA_API_PATH
        camunda_config.save()
        kownsl = Service.objects.create(api_type=APITypes.orc, api_root=KOWNSL_ROOT)
        kownsl_config = KownslConfig.get_solo()
        kownsl_config.service = kownsl
        kownsl_config.save()

        catalogus_url = (
            f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=catalogus_url,
            url=f"{CATALOGI_ROOT}zaaktypen/6496bb11-499e-43d3-a6ca-2a43ed704952",
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
        process_instance = factory(
            ProcessInstance,
            {
                "id": "205eae6b-d26f-11ea-86dc-e22fafe5f405",
                "definitionId": "beleid_opstellen:8:c76c8200-c766-11ea-86dc-e22fafe5f405",
                "businessKey": "",
                "caseInstanceId": "",
                "suspended": False,
                "tenantId": "",
            },
        )
        process_instance.tasks = [_get_task(**{"formKey": "zac:zetResultaat"})]
        cls.get_top_level_process_instances_patcher = patch(
            "zac.core.camunda.zet_resultaat.context.get_top_level_process_instances",
            return_value=[process_instance],
        )
        cls.resultaattype = generate_oas_component(
            "ztc", "schemas/ResultaatType", zaaktype=cls.zaaktype["url"]
        )

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
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")

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
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests?for_zaak={self.zaak['url']}",
            json=[
                {
                    **REVIEW_REQUEST,
                    "numAssignedUsers": REVIEW_REQUEST["numAdvices"]
                    + REVIEW_REQUEST["numApprovals"]
                    + 1,
                }
            ],
        )
        mock_resource_get(m, self.zaaktype)
        m.get(
            f"{CATALOGI_ROOT}resultaattypen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.resultaattype]),
        )
        checklist = {**CHECKLIST_OBJECT}
        checklist["record"]["data"]["answers"][0]["answer"] = ""
        with patch(
            "zac.objects.services.fetch_checklist_object", return_value=checklist
        ):
            with patch(
                "zac.objects.services.fetch_checklisttype_object",
                return_value=CHECKLISTTYPE_OBJECT,
            ):
                task_data = UserTaskData(task=task, context=_get_context(task))
        factory = APIRequestFactory()
        request = factory.get("/")

        serializer = ZetResultaatContextSerializer(
            instance=task_data,
            context={
                "request": Request(request),
            },
        )
        self.assertEqual(
            serializer.data["context"]["activiteiten"],
            [
                {
                    "created": "2013-01-23T11:42:42Z",
                    'createdBy': None,
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
                    "question": checklist["record"]["data"]["answers"][0]["question"],
                    "order": 1,
                    "choices": [{"name": "Ja", "value": "Ja"}],
                    "is_multiple_choice": True,
                }
            ],
        )
        self.assertEqual(
            serializer.data["context"]["taken"],
            [
                {
                    "id": TASK_DATA["id"],
                    "name": TASK_DATA["name"],
                    "created": "2013-01-23T11:42:42Z",
                    'createdBy': None,
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
