from copy import deepcopy
from unittest.mock import patch

from django.urls import reverse_lazy

import requests_mock
from freezegun import freeze_time
from rest_framework.test import APITestCase
from zgw_consumers.models import APITypes, Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import GroupFactory, SuperUserFactory
from zac.core.models import CoreConfig, MetaObjectTypesConfig
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.utils import mock_resource_get, paginated_response

from .utils import (
    BRONORGANISATIE,
    CATALOGI_ROOT,
    CHECKLIST_OBJECT,
    CHECKLIST_OBJECTTYPE,
    CHECKLIST_OBJECTTYPE_LATEST_VERSION,
    CHECKLISTTYPE_OBJECT,
    CHECKLISTTYPE_OBJECTTYPE,
    IDENTIFICATIE,
    OBJECTS_ROOT,
    OBJECTTYPES_ROOT,
    ZAAK_URL,
    ZAKEN_ROOT,
)


@requests_mock.Mocker()
@freeze_time("1999-12-31T23:59:59Z")
class ApiResponseTests(ESMixin, ClearCachesMixin, APITestCase):
    endpoint = reverse_lazy(
        "zaak-checklist",
        kwargs={"bronorganisatie": BRONORGANISATIE, "identificatie": IDENTIFICATIE},
    )

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(
            label="Zaken API", api_type=APITypes.zrc, api_root=ZAKEN_ROOT
        )
        Service.objects.create(
            label="Catalogi API",
            api_type=APITypes.ztc,
            api_root=CATALOGI_ROOT,
        )
        objects_service = Service.objects.create(
            api_type=APITypes.orc, api_root=OBJECTS_ROOT
        )
        objecttypes_service = Service.objects.create(
            api_type=APITypes.orc, api_root=OBJECTTYPES_ROOT
        )
        config = CoreConfig.get_solo()
        config.primary_objects_api = objects_service
        config.primary_objecttypes_api = objecttypes_service
        config.save()

        meta_config = MetaObjectTypesConfig.get_solo()
        meta_config.checklisttype_objecttype = CHECKLISTTYPE_OBJECTTYPE["url"]
        meta_config.checklist_objecttype = CHECKLIST_OBJECTTYPE["url"]
        meta_config.save()

        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
            domein="UTRE",
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=cls.catalogus["url"],
            url=f"{CATALOGI_ROOT}zaaktypen/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            identificatie="ZT1",
            omschrijving="ZT1",
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
            zaaktype=cls.zaaktype["url"],
            bronorganisatie=BRONORGANISATIE,
            identificatie=IDENTIFICATIE,
        )
        cls.user = SuperUserFactory.create(is_staff=True)

    def test_retrieve_checklist(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.catalogus)

        self.client.force_authenticate(user=self.user)

        with patch(
            "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
            return_value=CHECKLIST_OBJECT,
        ):
            with patch(
                "zac.contrib.objects.services.fetch_checklisttype_object",
                return_value=[CHECKLISTTYPE_OBJECT],
            ):
                response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)

    def test_retrieve_checklist_404(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.catalogus)

        self.client.force_authenticate(user=self.user)

        with patch(
            "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
            return_value=[],
        ):
            response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 404)

    def test_create_checklist(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, CHECKLIST_OBJECTTYPE)
        mock_resource_get(m, CHECKLIST_OBJECTTYPE_LATEST_VERSION)
        m.get(f"{OBJECTTYPES_ROOT}objecttypes", json=[CHECKLIST_OBJECTTYPE])
        m.post(f"{OBJECTS_ROOT}objects", json=CHECKLIST_OBJECT, status_code=201)
        m.post(f"{ZAKEN_ROOT}zaakobjecten", json=[], status_code=201)
        data = {
            "answers": [
                {"question": "Ja?", "answer": ""},
                {
                    "question": "Nee?",
                    "answer": "",
                },
            ],
        }

        self.client.force_authenticate(user=self.user)

        with patch(
            "zac.contrib.objects.services.fetch_checklisttype_object",
            return_value=[CHECKLISTTYPE_OBJECT],
        ):
            with patch(
                "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
                return_value=[],
            ):

                with patch(
                    "zac.contrib.objects.checklists.api.serializers.fetch_checklist",
                    return_value=None,
                ):
                    response = self.client.post(self.endpoint, data=data)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(),
            {
                "answers": [
                    {
                        "question": "Ja?",
                        "answer": "",
                        "remarks": "",
                        "document": "",
                        "groupAssignee": None,
                        "userAssignee": None,
                    },
                    {
                        "question": "Nee?",
                        "answer": "",
                        "remarks": "",
                        "document": "",
                        "groupAssignee": None,
                        "userAssignee": None,
                    },
                ],
                "lockedBy": None,
            },
        )

    def test_create_checklist_fail_no_checklisttype(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.catalogus)
        self.client.force_authenticate(user=self.user)

        with patch(
            "zac.contrib.objects.services.fetch_checklisttype_object",
            return_value=[],
        ):
            with patch(
                "zac.contrib.objects.services.fetch_checklist_object",
                return_value=[],
            ):
                response = self.client.post(self.endpoint, data={"answers": []})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {"nonFieldErrors": ["Checklisttype kan niet gevonden worden."]},
        )

    def test_create_checklist_fail_two_assignees_to_answer(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.catalogus)
        group = GroupFactory.create()
        data = {
            "answers": [
                {
                    "question": "Ja?",
                    "answer": "Ja",
                    "user_assignee": self.user.username,
                    "group_assignee": group.name,
                },
                {"question": "Nee?", "answer": ""},
            ],
        }

        self.client.force_authenticate(user=self.user)

        with patch(
            "zac.contrib.objects.services.fetch_checklisttype_object",
            return_value=[CHECKLISTTYPE_OBJECT],
        ):
            with patch(
                "zac.contrib.objects.services.fetch_checklist_object",
                return_value=[],
            ):
                response = self.client.post(self.endpoint, data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {
                "nonFieldErrors": [
                    "Een antwoord op een checklistvraag kan niet toegewezen worden aan zowel een gebruiker als een groep."
                ]
            },
        )

    def test_create_checklist_answer_not_found_in_mc(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.catalogus)
        data = {
            "answers": [
                {
                    "question": "Ja?",
                    "answer": "some-wrong-answer",
                },
                {"question": "Nee?", "answer": ""},
            ],
        }

        self.client.force_authenticate(user=self.user)

        with patch(
            "zac.contrib.objects.services.fetch_checklisttype_object",
            return_value=[CHECKLISTTYPE_OBJECT],
        ):
            with patch(
                "zac.contrib.objects.services.fetch_checklist_object",
                return_value=[],
            ):
                response = self.client.post(self.endpoint, data=data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {
                "nonFieldErrors": [
                    "Antwoord `some-wrong-answer` werd niet teruggevonden in de opties: ['Ja']."
                ]
            },
        )

    def test_create_checklist_answer_answers_wrong_question(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.catalogus)
        data = {
            "answers": [
                {
                    "question": "some-non-existent-question",
                    "answer": "",
                },
                {"question": "Nee?", "answer": ""},
            ],
        }

        self.client.force_authenticate(user=self.user)

        with patch(
            "zac.contrib.objects.services.fetch_checklisttype_object",
            return_value=[CHECKLISTTYPE_OBJECT],
        ):
            with patch(
                "zac.contrib.objects.services.fetch_checklist_object",
                return_value=[],
            ):
                response = self.client.post(self.endpoint, data=data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {
                "nonFieldErrors": [
                    "Antwoord met vraag: `some-non-existent-question` beantwoordt niet een vraag van het gerelateerde checklisttype."
                ]
            },
        )

    def test_update_checklist(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.catalogus)

        data = {
            "answers": [
                {"question": "Ja?", "answer": "Ja"},
                {"question": "Nee?", "answer": ""},
            ],
        }
        json_response = deepcopy(CHECKLIST_OBJECT)
        json_response["record"]["data"]["answers"] = data["answers"]
        m.patch(
            f"{OBJECTS_ROOT}objects/{CHECKLIST_OBJECT['uuid']}",
            json=json_response,
            status_code=200,
        )
        self.client.force_authenticate(user=self.user)
        # Put checklist
        with patch(
            "zac.contrib.objects.checklists.api.serializers.fetch_checklist_object",
            return_value=CHECKLIST_OBJECT,
        ):
            with patch(
                "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
                return_value=CHECKLIST_OBJECT,
            ):
                with patch(
                    "zac.contrib.objects.services.fetch_checklisttype_object",
                    return_value=[CHECKLISTTYPE_OBJECT],
                ):
                    response = self.client.put(self.endpoint, data=data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "answers": [
                    {
                        "question": "Ja?",
                        "answer": "Ja",
                        "remarks": "",
                        "document": "",
                        "groupAssignee": None,
                        "userAssignee": None,
                    },
                    {
                        "question": "Nee?",
                        "answer": "",
                        "remarks": "",
                        "document": "",
                        "groupAssignee": None,
                        "userAssignee": None,
                    },
                ],
                "lockedBy": None,
            },
        )
