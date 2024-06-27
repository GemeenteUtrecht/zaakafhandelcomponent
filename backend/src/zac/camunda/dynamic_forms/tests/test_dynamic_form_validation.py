from pathlib import Path
from unittest.mock import patch

from django.urls import reverse

import requests_mock
from django_camunda.client import get_client
from django_camunda.models import CamundaConfig
from django_camunda.utils import underscoreize
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import SuperUserFactory
from zac.camunda.data import Task
from zac.core.tests.utils import ClearCachesMixin, mock_parallel
from zac.tests.utils import paginated_response

CAMUNDA_ROOT = "https://some.camunda.nl/"
CAMUNDA_API_PATH = "engine-rest/"
CAMUNDA_URL = f"{CAMUNDA_ROOT}{CAMUNDA_API_PATH}"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"
CATALOGI_ROOT = "https://open-zaak.nl/catalogi/api/v1/"
CAMUNDA_ROOT = "https://some.camunda.nl/"
CAMUNDA_API_PATH = "engine-rest/"
CAMUNDA_URL = f"{CAMUNDA_ROOT}{CAMUNDA_API_PATH}"
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

FILES_DIR = Path(__file__).parent

with open(FILES_DIR / "dynamic-form-eigenschap.bpmn", "r") as bpmn:
    BPMN_DATA = {
        "id": "aProcDefId",
        "bpmn20Xml": bpmn.read(),
    }


def _get_task(**overrides):
    data = underscoreize({**TASK_DATA, **overrides})
    return factory(Task, data)


def _get_camunda_client():
    config = CamundaConfig.get_solo()
    config.root_url = CAMUNDA_ROOT
    config.rest_api_path = CAMUNDA_API_PATH
    config.save()
    return get_client()


@requests_mock.Mocker()
class ReadDynamicFormContextTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.maxDiff = None
        cls.user = SuperUserFactory.create()
        cls.patch_get_client_bpmn = patch(
            "django_camunda.bpmn.get_client", return_value=_get_camunda_client()
        )
        cls.mock_parallel = patch(
            "zac.core.services.parallel", return_value=mock_parallel()
        )

        cls.task_endpoint = reverse(
            "user-task-data", kwargs={"task_id": TASK_DATA["id"]}
        )

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)

        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
            domein="DOMEI",
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=cls.catalogus["url"],
            url=f"{CATALOGI_ROOT}zaaktypen/6ba8130e-29c0-4105-8b67-0fa861f76923",
            identificatie="ZAAKTYPE-01",
            omschrijving="ZT1",
        )

    def setUp(self) -> None:
        super().setUp()
        self.client.force_authenticate(self.user)
        self.patch_get_client_bpmn.start()
        self.addCleanup(self.patch_get_client_bpmn.stop)
        self.mock_parallel.start()
        self.addCleanup(self.mock_parallel.stop)

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(),
    )
    def test_get_context_no_eigenschappen_enum_from_camunda_values(self, m, gt):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        # mock for zac.camunda.forms.get_bpmn
        m.get(
            f"{CAMUNDA_URL}process-definition/aProcDefId/xml",
            headers={"Content-Type": "application/json"},
            json=BPMN_DATA,
        )

        # mock for zac.camunda.dynamic_forms.utils.get_catalogi
        m.get(f"{CATALOGI_ROOT}catalogussen", json=paginated_response([]))

        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.task_endpoint)
        self.assertEqual(
            response.json(),
            {
                "form": "",
                "task": {
                    "id": TASK_DATA["id"],
                    "name": TASK_DATA["name"],
                    "created": "2013-01-23T11:42:42Z",
                    "hasForm": False,
                    "assigneeType": "",
                    "canCancelTask": False,
                    "formKey": TASK_DATA["formKey"],
                    "assignee": None,
                },
                "context": {
                    "formFields": [
                        {
                            "name": "formfield-01",
                            "label": "EIGENSCHAP",
                            "inputType": "string",
                            "value": "waarde1",
                            "spec": None,
                        },
                        {
                            "name": "formfield-02",
                            "label": "SOMELABEL-02",
                            "inputType": "enum",
                            "value": None,
                            "enum": [["first", "First"], ["second", "Second"]],
                            "spec": None,
                        },
                        {
                            "name": "formfield-03",
                            "label": "LONG-FIELD",
                            "inputType": "int",
                            "value": None,
                            "spec": None,
                        },
                    ]
                },
            },
        )

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(),
    )
    def test_get_context_with_eigenschap_enum_from_waardenverzameling(self, m, gt):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        # mock for zac.camunda.forms.get_bpmn
        m.get(
            f"{CAMUNDA_URL}process-definition/aProcDefId/xml",
            headers={"Content-Type": "application/json"},
            json=BPMN_DATA,
        )

        # mock for zac.camunda.dynamic_forms.utils.get_catalogi
        m.get(f"{CATALOGI_ROOT}catalogussen", json=paginated_response([self.catalogus]))

        # mock for zac.camunda.dynamic_forms.utils.get_zaaktypen
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.catalogus['url']}",
            json=paginated_response([self.zaaktype]),
        )
        # mock for zac.camunda.dynamic_forms.utils.get_eigenschappen_for_zaaktypen
        eigenschap = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            zaaktype=self.zaaktype["url"],
            naam="EIGENSCHAP",
            specificatie={
                "groep": "dummy",
                "formaat": "tekst",
                "lengte": "7",
                "kardinaliteit": "1",
                "waardenverzameling": ["waarde1", "waarde2"],
            },
            url=f"{CATALOGI_ROOT}eigenschappen/88e425b4-8b8f-4a35-b577-20d63ce24d9c",
        )
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([eigenschap]),
        )

        self.client.force_authenticate(user=self.user)
        with patch(
            "zac.camunda.dynamic_forms.utils.fetch_zaaktypeattributen_objects_for_zaaktype",
            return_value=[],
        ):
            response = self.client.get(self.task_endpoint)

        self.assertEqual(
            response.json(),
            {
                "form": "",
                "task": {
                    "id": TASK_DATA["id"],
                    "name": TASK_DATA["name"],
                    "created": "2013-01-23T11:42:42Z",
                    "hasForm": False,
                    "assigneeType": "",
                    "canCancelTask": False,
                    "formKey": TASK_DATA["formKey"],
                    "assignee": None,
                },
                "context": {
                    "formFields": [
                        {
                            "name": "formfield-01",
                            "label": "EIGENSCHAP",
                            "inputType": "enum",  # <- NOT STRING - test successful
                            "value": "waarde1",
                            "enum": [
                                ["waarde1", "waarde1"],
                                ["waarde2", "waarde2"],
                            ],  # <- values from eigenschap specificatie waardenverzameling
                            "spec": {
                                "enum": [
                                    {"label": "waarde1", "value": "waarde1"},
                                    {"label": "waarde2", "value": "waarde2"},
                                ],
                                "maxLength": 7,
                                "minLength": 1,
                                "type": "string",
                            },
                        },
                        {
                            "name": "formfield-02",
                            "label": "SOMELABEL-02",
                            "inputType": "enum",
                            "value": None,
                            "enum": [["first", "First"], ["second", "Second"]],
                            "spec": None,
                        },
                        {
                            "name": "formfield-03",
                            "label": "LONG-FIELD",
                            "inputType": "int",
                            "value": None,
                            "spec": None,
                        },
                    ]
                },
            },
        )

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(),
    )
    def test_get_context_with_eigenschap_enum_from_zaaktype_attributes(self, m, gt):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        # mock for zac.camunda.forms.get_bpmn
        m.get(
            f"{CAMUNDA_URL}process-definition/aProcDefId/xml",
            headers={"Content-Type": "application/json"},
            json=BPMN_DATA,
        )

        # mock for zac.camunda.dynamic_forms.utils.get_catalogi
        m.get(f"{CATALOGI_ROOT}catalogussen", json=paginated_response([self.catalogus]))

        # mock for zac.camunda.dynamic_forms.utils.get_zaaktypen
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.catalogus['url']}",
            json=paginated_response([self.zaaktype]),
        )
        # mock for zac.camunda.dynamic_forms.utils.get_eigenschappen_for_zaaktypen
        eigenschap = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            zaaktype=self.zaaktype["url"],
            naam="EIGENSCHAP",
            specificatie={
                "groep": "dummy",
                "formaat": "tekst",
                "lengte": "7",
                "kardinaliteit": "1",
                "waardenverzameling": ["waarde1", "waarde2"],
            },
            url=f"{CATALOGI_ROOT}eigenschappen/88e425b4-8b8f-4a35-b577-20d63ce24d9c",
        )
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([eigenschap]),
        )

        zaaktype_attributes = [
            {
                "enum": ["zaaktype-attribuut-01", "zaaktype-attribuut-02"],
                "naam": eigenschap["naam"],
                "waarde": "",
                "zaaktypeCatalogus": self.catalogus["domein"],
                "zaaktypeIdentificaties": [
                    self.zaaktype["identificatie"],
                ],
            }
        ]

        self.client.force_authenticate(user=self.user)
        with patch(
            "zac.camunda.dynamic_forms.utils.fetch_zaaktypeattributen_objects_for_zaaktype",
            return_value=zaaktype_attributes,
        ):
            response = self.client.get(self.task_endpoint)

        self.assertEqual(
            response.json(),
            {
                "form": "",
                "task": {
                    "id": TASK_DATA["id"],
                    "name": TASK_DATA["name"],
                    "created": "2013-01-23T11:42:42Z",
                    "hasForm": False,
                    "assigneeType": "",
                    "canCancelTask": False,
                    "formKey": TASK_DATA["formKey"],
                    "assignee": None,
                },
                "context": {
                    "formFields": [
                        {
                            "name": "formfield-01",
                            "label": "EIGENSCHAP",
                            "inputType": "enum",  # <- NOT STRING - test successful
                            "value": "waarde1",
                            "enum": [
                                ["zaaktype-attribuut-01", "zaaktype-attribuut-01"],
                                ["zaaktype-attribuut-02", "zaaktype-attribuut-02"],
                            ],  # <- values from eigenschap specificatie waardenverzameling
                            "spec": {
                                "enum": [
                                    {
                                        "label": "zaaktype-attribuut-01",
                                        "value": "zaaktype-attribuut-01",
                                    },
                                    {
                                        "label": "zaaktype-attribuut-02",
                                        "value": "zaaktype-attribuut-02",
                                    },
                                ],
                                "maxLength": 7,
                                "minLength": 1,
                                "type": "string",
                            },
                        },
                        {
                            "name": "formfield-02",
                            "label": "SOMELABEL-02",
                            "inputType": "enum",
                            "value": None,
                            "enum": [["first", "First"], ["second", "Second"]],
                            "spec": None,
                        },
                        {
                            "name": "formfield-03",
                            "label": "LONG-FIELD",
                            "inputType": "int",
                            "value": None,
                            "spec": None,
                        },
                    ]
                },
            },
        )


@requests_mock.Mocker()
class WriteDynamicFormContextTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.maxDiff = None
        cls.user = SuperUserFactory.create()
        cls.patch_get_client_bpmn = patch(
            "django_camunda.bpmn.get_client", return_value=_get_camunda_client()
        )
        cls.mock_parallel = patch(
            "zac.core.services.parallel", return_value=mock_parallel()
        )

        cls.task_endpoint = reverse(
            "user-task-data", kwargs={"task_id": TASK_DATA["id"]}
        )

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)

        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
            domein="DOMEI",
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=cls.catalogus["url"],
            url=f"{CATALOGI_ROOT}zaaktypen/6ba8130e-29c0-4105-8b67-0fa861f76923",
            identificatie="ZAAKTYPE-01",
            omschrijving="ZT1",
        )

    def setUp(self) -> None:
        super().setUp()
        self.client.force_authenticate(self.user)
        self.patch_get_client_bpmn.start()
        self.addCleanup(self.patch_get_client_bpmn.stop)
        self.mock_parallel.start()
        self.addCleanup(self.mock_parallel.stop)

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(),
    )
    def test_no_eigenschappen_validation_from_camunda_enum_values(self, m, gt):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        # mock for zac.camunda.forms.get_bpmn
        m.get(
            f"{CAMUNDA_URL}process-definition/aProcDefId/xml",
            headers={"Content-Type": "application/json"},
            json=BPMN_DATA,
        )

        # mock for zac.camunda.dynamic_forms.utils.get_catalogi
        m.get(f"{CATALOGI_ROOT}catalogussen", json=paginated_response([]))

        self.client.force_authenticate(user=self.user)

        with self.subTest("Fail validation on enum"):
            response = self.client.put(
                self.task_endpoint,
                {
                    "formfield-01": "some-value-01",
                    "formfield-02": "some-other-value",
                    "formfield-03": 3,
                },
            )
            self.assertEqual(
                response.json()["invalid_params"],
                [
                    {
                        "code": "invalid_choice",
                        "name": "formfield-02",
                        "reason": '"some-other-value" is een ongeldige keuze.',
                    }
                ],
            )

        with self.subTest("Success validation on enum"):
            with patch("zac.camunda.api.views.set_assignee_and_complete_task"):
                response = self.client.put(
                    self.task_endpoint,
                    {
                        "formfield-01": "some-value-01",
                        "formfield-02": "second",
                        "formfield-03": 3,
                    },
                )
                self.assertEqual(response.status_code, 204)

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(),
    )
    def test_validate_form_field_eigenschap_enum_from_waardenverzameling(self, m, gt):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        # mock for zac.camunda.forms.get_bpmn
        m.get(
            f"{CAMUNDA_URL}process-definition/aProcDefId/xml",
            headers={"Content-Type": "application/json"},
            json=BPMN_DATA,
        )

        # mock for zac.camunda.dynamic_forms.utils.get_catalogi
        m.get(f"{CATALOGI_ROOT}catalogussen", json=paginated_response([self.catalogus]))

        # mock for zac.camunda.dynamic_forms.utils.get_zaaktypen
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.catalogus['url']}",
            json=paginated_response([self.zaaktype]),
        )
        # mock for zac.camunda.dynamic_forms.utils.get_eigenschappen_for_zaaktypen
        eigenschap = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            zaaktype=self.zaaktype["url"],
            naam="EIGENSCHAP",
            specificatie={
                "groep": "dummy",
                "formaat": "tekst",
                "lengte": "7",
                "kardinaliteit": "1",
                "waardenverzameling": ["waarde1", "waarde2"],
            },
            url=f"{CATALOGI_ROOT}eigenschappen/88e425b4-8b8f-4a35-b577-20d63ce24d9c",
        )
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([eigenschap]),
        )

        self.client.force_authenticate(user=self.user)
        with patch(
            "zac.camunda.dynamic_forms.utils.fetch_zaaktypeattributen_objects_for_zaaktype",
            return_value=[],
        ):
            with self.subTest("Fail validation on enum"):
                response = self.client.put(
                    self.task_endpoint,
                    {
                        "formfield-01": "some-value-01",
                        "formfield-02": "second",
                        "formfield-03": 3,
                    },
                )
                self.assertEqual(
                    response.json()["invalid_params"],
                    [
                        {
                            "code": "invalid_choice",
                            "name": "formfield-01",
                            "reason": '"some-value-01" is een ongeldige keuze.',
                        }
                    ],
                )

            with self.subTest("Success validation on enum"):
                with patch("zac.camunda.api.views.set_assignee_and_complete_task"):
                    response = self.client.put(
                        self.task_endpoint,
                        {
                            "formfield-01": "waarde1",
                            "formfield-02": "second",
                            "formfield-03": 3,
                        },
                    )
                    self.assertEqual(response.status_code, 204)

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(),
    )
    def test_validate_form_field_eigenschap_enum_from_zaaktype_attributes(self, m, gt):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        # mock for zac.camunda.forms.get_bpmn
        m.get(
            f"{CAMUNDA_URL}process-definition/aProcDefId/xml",
            headers={"Content-Type": "application/json"},
            json=BPMN_DATA,
        )

        # mock for zac.camunda.dynamic_forms.utils.get_catalogi
        m.get(f"{CATALOGI_ROOT}catalogussen", json=paginated_response([self.catalogus]))

        # mock for zac.camunda.dynamic_forms.utils.get_zaaktypen
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.catalogus['url']}",
            json=paginated_response([self.zaaktype]),
        )
        # mock for zac.camunda.dynamic_forms.utils.get_eigenschappen_for_zaaktypen
        eigenschap = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            zaaktype=self.zaaktype["url"],
            naam="EIGENSCHAP",
            specificatie={
                "groep": "dummy",
                "formaat": "tekst",
                "lengte": "7",
                "kardinaliteit": "1",
                "waardenverzameling": ["waarde1", "waarde2"],
            },
            url=f"{CATALOGI_ROOT}eigenschappen/88e425b4-8b8f-4a35-b577-20d63ce24d9c",
        )
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([eigenschap]),
        )

        self.client.force_authenticate(user=self.user)

        with self.subTest("Fail validation on enum"):
            super().setUp()  # clear cache
            zaaktype_attributes = [
                {
                    "enum": ["zaaktype-attribuut-01", "zaaktype-attribuut-02"],
                    "naam": eigenschap["naam"],
                    "waarde": "",
                    "zaaktypeCatalogus": self.catalogus["domein"],
                    "zaaktypeIdentificaties": [
                        self.zaaktype["identificatie"],
                    ],
                }
            ]
            with patch(
                "zac.camunda.dynamic_forms.utils.fetch_zaaktypeattributen_objects_for_zaaktype",
                return_value=zaaktype_attributes,
            ):
                response = self.client.put(
                    self.task_endpoint,
                    {
                        "formfield-01": "some-value-01",
                        "formfield-02": "second",
                        "formfield-03": 3,
                    },
                )
                self.assertEqual(
                    response.json()["invalid_params"],
                    [
                        {
                            "code": "invalid_choice",
                            "name": "formfield-01",
                            "reason": '"some-value-01" is een ongeldige keuze.',
                        }
                    ],
                )

        with self.subTest("Fail validation on enum - too long"):
            super().setUp()  # clear cache
            zaaktype_attributes = [
                {
                    "enum": ["zaaktype-attribuut-01", "zaaktype-attribuut-02"],
                    "naam": eigenschap["naam"],
                    "waarde": "",
                    "zaaktypeCatalogus": self.catalogus["domein"],
                    "zaaktypeIdentificaties": [
                        self.zaaktype["identificatie"],
                    ],
                }
            ]
            with patch(
                "zac.camunda.dynamic_forms.utils.fetch_zaaktypeattributen_objects_for_zaaktype",
                return_value=zaaktype_attributes,
            ):
                with patch("zac.camunda.api.views.set_assignee_and_complete_task"):
                    response = self.client.put(
                        self.task_endpoint,
                        {
                            "formfield-01": "zaaktype-attribuut-01",
                            "formfield-02": "second",
                            "formfield-03": 3,
                        },
                    )
                    self.assertEqual(
                        response.json()["invalid_params"],
                        [
                            {
                                "code": "invalid",
                                "name": "formfield-01",
                                "reason": "A ZAAKEIGENSCHAP with `name`: EIGENSCHAP "
                                "requires a maximum length of 7.",
                            }
                        ],
                    )

        with self.subTest("Success validation on enum - just right"):
            super().setUp()  # clear cache
            zaaktype_attributes = [
                {
                    "enum": ["hihihoo", "hohohii"],
                    "naam": eigenschap["naam"],
                    "waarde": "",
                    "zaaktypeCatalogus": self.catalogus["domein"],
                    "zaaktypeIdentificaties": [
                        self.zaaktype["identificatie"],
                    ],
                }
            ]
            with patch(
                "zac.camunda.dynamic_forms.utils.fetch_zaaktypeattributen_objects_for_zaaktype",
                return_value=zaaktype_attributes,
            ):
                with patch("zac.camunda.api.views.set_assignee_and_complete_task"):
                    response = self.client.put(
                        self.task_endpoint,
                        {
                            "formfield-01": "hihihoo",
                            "formfield-02": "second",
                            "formfield-03": 3,
                        },
                    )
                    self.assertEqual(response.status_code, 204)
