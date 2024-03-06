from copy import deepcopy
from unittest.mock import patch

from django.urls import reverse_lazy

import requests_mock
from freezegun import freeze_time
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.models import APITypes, Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import GroupFactory, SuperUserFactory
from zac.contrib.objects.services import lock_checklist_for_zaak
from zac.core.models import CoreConfig, MetaObjectTypesConfig
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.utils import mock_resource_get, paginated_response
from zgw.models.zrc import Zaak

from ..models import ChecklistLock
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
    ChecklistLockFactory,
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
                {"question": "Ja?", "answer": "Ja"},
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
                return_value=CHECKLIST_OBJECT,
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
                        "answer": "Ja",
                        "remarks": "",
                        "document": "",
                        "groupAssignee": None,
                        "userAssignee": None,
                        "created": "1999-12-31T23:59:59Z",
                    },
                    {
                        "question": "Nee?",
                        "answer": "",
                        "remarks": "",
                        "document": "",
                        "groupAssignee": None,
                        "userAssignee": None,
                        "created": "1999-12-31T23:59:59Z",
                    },
                ],
                "locked": False,
                "lockedBy": None,
                "zaak": self.zaak["url"],
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
                {"question": "Ja?", "answer": "Ja", "userAssignee": self.user.username},
                {"question": "Nee?", "answer": "Nee"},
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
            "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
            side_effect=[CHECKLIST_OBJECT, json_response],
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
                        "userAssignee": {
                            "email": self.user.email,
                            "firstName": self.user.first_name,
                            "fullName": self.user.get_full_name(),
                            "lastName": self.user.last_name,
                            "username": self.user.username,
                        },
                        "created": "1999-12-31T23:59:59Z",
                    },
                    {
                        "question": "Nee?",
                        "answer": "Nee",
                        "remarks": "",
                        "document": "",
                        "groupAssignee": None,
                        "userAssignee": None,
                        "created": "1999-12-31T23:59:59Z",
                    },
                ],
                "locked": False,
                "lockedBy": None,
                "zaak": self.zaak["url"],
            },
        )

        self.assertEqual(
            m.last_request.json(),
            {
                "record": {
                    "index": 1,
                    "typeVersion": 3,
                    "data": {
                        "answers": [
                            {
                                "answer": "Ja",
                                "question": "Ja?",
                                "groupAssignee": None,
                                "userAssignee": {
                                    "email": self.user.email,
                                    "firstName": self.user.first_name,
                                    "fullName": self.user.get_full_name(),
                                    "lastName": self.user.last_name,
                                    "username": self.user.username,
                                },
                                "created": "1999-12-31T23:59:59+00:00",
                                "document": "",
                                "remarks": "",
                            },
                            {
                                "question": "Nee?",
                                "answer": "Nee",
                                "remarks": "",
                                "document": "",
                                "groupAssignee": None,
                                "userAssignee": None,
                                "created": "1999-12-31T23:59:59+00:00",
                            },
                        ],
                        "zaak": self.zaak["url"],
                        "locked": False,
                    },
                    "geometry": "None",
                    "startAt": "1999-12-31",
                    "endAt": "None",
                    "registrationAt": "1999-12-31",
                    "correctionFor": 1,
                    "correctedBy": self.user.username,
                }
            },
        )

    def test_update_checklist_no_update_object_called(self, m):
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
            "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
            side_effect=[CHECKLIST_OBJECT, json_response],
        ):
            with patch(
                "zac.contrib.objects.services.fetch_checklisttype_object",
                return_value=[CHECKLISTTYPE_OBJECT],
            ):
                with patch(
                    "zac.contrib.objects.checklists.api.serializers.update_object_record_data"
                ) as mock_update_object:
                    response = self.client.put(self.endpoint, data=data)

        mock_update_object.assert_not_called()
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
                        "created": "1999-12-31T23:59:59Z",
                    },
                    {
                        "question": "Nee?",
                        "answer": "",
                        "remarks": "",
                        "document": "",
                        "groupAssignee": None,
                        "userAssignee": None,
                        "created": "1999-12-31T23:59:59Z",
                    },
                ],
                "locked": False,
                "lockedBy": None,
                "zaak": self.zaak["url"],
            },
        )

    def test_lock_checklist(self, m):
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

        m.patch(
            f"{OBJECTS_ROOT}objects/{CHECKLIST_OBJECT['uuid']}",
            json=CHECKLIST_OBJECT,
            status_code=200,
        )
        self.client.force_authenticate(user=self.user)
        lock_endpoint = reverse_lazy(
            "lock-zaak-checklist",
            kwargs={"bronorganisatie": BRONORGANISATIE, "identificatie": IDENTIFICATIE},
        )

        with patch(
            "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
            return_value=deepcopy(CHECKLIST_OBJECT),
        ):
            response = self.client.post(lock_endpoint)

        self.assertEqual(response.status_code, 204)

    def test_lock_checklist_but_already_locked(self, m):
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
        lock_endpoint = reverse_lazy(
            "lock-zaak-checklist",
            kwargs={"bronorganisatie": BRONORGANISATIE, "identificatie": IDENTIFICATIE},
        )
        lock = ChecklistLockFactory.create(url=CHECKLIST_OBJECT["url"], user=self.user)
        with patch(
            "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
            return_value=CHECKLIST_OBJECT,
        ):
            response = self.client.post(lock_endpoint)

        self.assertEqual(response.status_code, 200)
        lock.delete()

    def test_unlock_checklist(self, m):
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

        m.patch(
            f"{OBJECTS_ROOT}objects/{CHECKLIST_OBJECT['uuid']}",
            json=CHECKLIST_OBJECT,
            status_code=200,
        )
        self.client.force_authenticate(user=self.user)
        unlock_endpoint = reverse_lazy(
            "unlock-zaak-checklist",
            kwargs={"bronorganisatie": BRONORGANISATIE, "identificatie": IDENTIFICATIE},
        )
        lock = ChecklistLockFactory.create(url=CHECKLIST_OBJECT["url"], user=self.user)
        with patch(
            "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
            return_value=CHECKLIST_OBJECT,
        ):
            response = self.client.post(unlock_endpoint)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            ChecklistLock.objects.filter(url=CHECKLIST_OBJECT["url"]).exists()
        )

    def test_unlock_checklist_but_checklist_is_not_locked(self, m):
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
        unlock_endpoint = reverse_lazy(
            "unlock-zaak-checklist",
            kwargs={"bronorganisatie": BRONORGANISATIE, "identificatie": IDENTIFICATIE},
        )
        with patch(
            "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
            return_value=CHECKLIST_OBJECT,
        ):
            response = self.client.post(unlock_endpoint)

        self.assertEqual(response.status_code, 404)

    def test_lock_checklist_for_zaak(self, m):
        checklist_object = deepcopy(CHECKLIST_OBJECT)
        answer = checklist_object["record"]["data"]["answers"][0]
        answer["userAssignee"] = "some-user"
        answer["answer"] = ""

        with patch(
            "zac.contrib.objects.services.fetch_checklist_object",
            return_value=checklist_object,
        ) as mock_fetch_checklist_object:
            with patch(
                "zac.contrib.objects.services.update_object_record_data"
            ) as mock_update_object_record_data:
                lock_checklist_for_zaak(factory(Zaak, self.zaak))

        mock_fetch_checklist_object.assert_called_once()
        mock_update_object_record_data.assert_called_once()
