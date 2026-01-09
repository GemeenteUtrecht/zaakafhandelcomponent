from copy import deepcopy
from os import path
from unittest.mock import patch

from django.urls import reverse_lazy

import requests_mock
from django_camunda.client import get_client
from django_camunda.models import CamundaConfig
from django_camunda.utils import underscoreize
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import Eigenschap, InformatieObjectType, ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.api_models.zaken import ZaakEigenschap
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.accounts.models import User
from zac.accounts.tests.factories import UserFactory
from zac.camunda.constants import AssigneeTypeChoices
from zac.camunda.data import Task
from zac.contrib.objects.kownsl.constants import KownslTypes
from zac.contrib.objects.kownsl.tests.factories import (
    CATALOGI_ROOT,
    DOCUMENT_URL,
    DOCUMENTS_ROOT,
    OBJECTS_ROOT,
    OBJECTTYPES_ROOT,
    ZAAK_URL,
    ZAKEN_ROOT,
    advice_factory,
    approval_factory,
    review_object_factory,
    review_object_type_factory,
    review_request_factory,
    review_request_object_type_factory,
    reviews_factory,
)
from zac.core.models import CoreConfig, MetaObjectTypesConfig
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.api import create_informatieobject_document
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.mixins import FreezeTimeMixin
from zac.tests.utils import mock_resource_get, paginated_response
from zgw.models.zrc import Zaak

from ...services import factory_review_request, factory_reviews

CATALOGUS_URL = f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
CAMUNDA_ROOT = "https://some.camunda.nl/"
CAMUNDA_API_PATH = "engine-rest/"
CAMUNDA_URL = f"{CAMUNDA_ROOT}{CAMUNDA_API_PATH}"
REVIEW_REQUEST_OBJECTTYPE = review_request_object_type_factory()
REVIEW_OBJECTTYPE = review_object_type_factory()


def _get_camunda_client():
    config = CamundaConfig.get_solo()
    config.root_url = CAMUNDA_ROOT
    config.rest_api_path = CAMUNDA_API_PATH
    config.save()
    return get_client()


@requests_mock.Mocker()
class KownslReviewsTests(FreezeTimeMixin, ClearCachesMixin, APITestCase):
    frozen_time = "2022-04-14T15:51:09.830235"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
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
        meta_config.review_request_objecttype = REVIEW_REQUEST_OBJECTTYPE["url"]
        meta_config.review_objecttype = REVIEW_OBJECTTYPE["url"]
        meta_config.save()

        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )
        cls.eigenschap = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            zaaktype=cls.zaaktype["url"],
            naam="some-property",
            specificatie={
                "groep": "dummy",
                "formaat": "tekst",
                "lengte": "3",
                "kardinaliteit": "1",
                "waardenverzameling": [],
            },
            url=f"{CATALOGI_ROOT}eigenschappen/68b5b40c-c479-4008-a57b-a268b280df99",
        )
        cls.zaak_json = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            zaaktype=cls.zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            startdatum="2020-12-25",
            uiterlijkeEinddatumAfdoening="2021-01-04",
        )
        cls.zaakeigenschap = generate_oas_component(
            "zrc",
            "schemas/ZaakEigenschap",
            zaak=cls.zaak_json["url"],
            eigenschap=cls.eigenschap["url"],
            naam=cls.eigenschap["naam"],
            waarde="bar",
        )
        cls.informatieobjecttype = generate_oas_component(
            "ztc",
            "schemas/InformatieObjectType",
            url=f"{CATALOGI_ROOT}informatieobjecttypen/d5d7285d-ce95-4f9e-a36f-181f1c642aa6",
            omschrijving="bijlage",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )
        cls.document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=DOCUMENT_URL,
            identificatie="DOC-2020-007",
            bronorganisatie="123456782",
            informatieobjecttype=cls.informatieobjecttype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            bestandsomvang=10,
            versie=1,
        )

        # Dict to models
        cls.zaak = factory(Zaak, cls.zaak_json)
        cls.zaak.zaaktype = factory(ZaakType, cls.zaaktype)
        cls.zaakeigenschap = factory(ZaakEigenschap, cls.zaakeigenschap)
        cls.zaakeigenschap.eigenschap = factory(Eigenschap, cls.eigenschap)

        # Mock DRC components
        cls.document = factory(Document, cls.document)
        cls.document.informatieobjecttype = factory(
            InformatieObjectType, cls.informatieobjecttype
        )
        cls.document.last_edited_date = None  # avoid patching fetching audit trail

        # Create elasticsearch document
        cls.es_document = create_informatieobject_document(cls.document)

        cls.zaak = factory(Zaak, cls.zaak_json)

        cls.review_request = review_request_factory()
        cls.advice = advice_factory()
        cls.reviews_advice = reviews_factory(reviews=[cls.advice])

        cls.review_object = review_object_factory(record__data=cls.reviews_advice)

        # Mock camunda task
        cls.task = {
            "id": "fc9c465d-b0d7-11ec-a5f0-32fe9303dc32",
            "name": "Adviseren",
            "assignee": None,
            "created": "2022-03-31T09:50:24.420+0000",
            "due": None,
            "follow_up": None,
            "delegation_state": None,
            "description": None,
            "execution_id": "fc9c4659-b0d7-11ec-a5f0-32fe9303dc32",
            "owner": None,
            "parent_task_id": None,
            "priority": 50,
            "process_definition_id": "Beleid_opstellen:6:85ff7b20-a149-11ec-a0c6-dec9c846e7c7",
            "process_instance_id": cls.review_request["metadata"]["processInstanceId"],
            "task_definition_key": "submitAdvice",
            "case_execution_id": None,
            "case_instance_id": None,
            "case_definition_id": None,
            "suspended": False,
            "form_key": None,
            "tenant_id": None,
        }

        # Make sure all users associated to the REVIEW REQUEST exist
        users = deepcopy(
            [
                cls.review_request["assignedUsers"][0]["userAssignees"][0],
                cls.review_request["assignedUsers"][1]["userAssignees"][0],
                cls.review_request["requester"],
            ]
        )
        # del full_name
        for user in users:
            del user["fullName"]
            UserFactory.create(**underscoreize(user))

        cls.user = User.objects.get(
            username=cls.review_request["requester"]["username"]
        )

        cls.approval_url = reverse_lazy(
            "kownsl:reviewrequest-approval",
            kwargs={"request_uuid": cls.review_request["id"]},
        )
        cls.review_url = reverse_lazy(
            "kownsl:reviewrequest-advice",
            kwargs={"request_uuid": cls.review_request["id"]},
        )

    def setUp(self):
        patchers = [
            patch(
                "zac.contrib.objects.kownsl.data.get_zaakeigenschappen",
                return_value=[self.zaakeigenschap],
            ),
            patch(
                "zac.contrib.objects.kownsl.api.views.get_zaak", return_value=self.zaak
            ),
            patch(
                "zac.contrib.objects.kownsl.data.search_informatieobjects",
                return_value=[self.es_document],
            ),
            patch(
                "zac.contrib.dowc.utils.get_supported_extensions",
                return_value=[path.splitext(self.es_document.bestandsnaam)],
            ),
            patch(
                "zac.contrib.objects.services.fetch_reviews",
                return_value=self.review_object,
            ),
            patch("django_camunda.api.get_client", return_value=_get_camunda_client()),
        ]
        for p in patchers:
            p.start()
            self.addCleanup(p.stop)

        super().setUp()

    def test_fail_get_approval_view_no_assignee(self, m):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.approval_url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "assignee",
                    "code": "required",
                    "reason": "Dit veld is vereist.",
                }
            ],
        )

    def test_fail_get_approval_review_request_not_found(self, m):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")

        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([REVIEW_REQUEST_OBJECTTYPE]),
        )
        m.post(
            f"{OBJECTS_ROOT}objects/search?pageSize=100",
            json=paginated_response([]),
        )

        self.client.force_authenticate(user=self.user)
        url = self.approval_url + f"?assignee={AssigneeTypeChoices.user}:{self.user}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_fail_get_approval_zaak_not_found(self, m):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        m.get(self.zaak.url, status_code=404)

        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([REVIEW_REQUEST_OBJECTTYPE]),
        )
        m.post(
            f"{OBJECTS_ROOT}objects/search?pageSize=100",
            json=paginated_response([]),
        )

        self.client.force_authenticate(user=self.user)
        url = self.approval_url + f"?assignee={AssigneeTypeChoices.user}:{self.user}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_success_get_approval_review_request(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        mock_resource_get(m, self.zaak_json)
        rr = factory_review_request(self.review_request)
        rr.fetched_reviews = True
        rr.reviews = []
        rr.review_type = KownslTypes.approval

        self.client.force_authenticate(user=self.user)
        url = self.approval_url + f"?assignee={AssigneeTypeChoices.user}:{self.user}"

        rr.zaakeigenschappen = [self.zaakeigenschap.url]
        with patch(
            "zac.contrib.objects.kownsl.api.views.get_review_request",
            return_value=rr,
        ):
            response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "created": self.review_request["created"],
                "documents": [],
                "id": self.review_request["id"],
                "isBeingReconfigured": self.review_request["isBeingReconfigured"],
                "locked": self.review_request["locked"],
                "lockReason": self.review_request["lockReason"],
                "openReviews": [
                    {
                        "deadline": "2022-04-14",
                        "groups": [],
                        "users": ["Some First Some Last"],
                    },
                    {
                        "deadline": "2022-04-15",
                        "groups": [],
                        "users": ["Some Other First Some Last"],
                    },
                ],
                "requester": self.review_request["requester"],
                "reviewType": KownslTypes.approval,
                "toelichting": self.review_request["toelichting"],
                "zaak": {
                    "identificatie": self.zaak.identificatie,
                    "bronorganisatie": self.zaak.bronorganisatie,
                    "url": self.zaak.url,
                },
                "zaakeigenschappen": [
                    {
                        "url": self.zaakeigenschap.url,
                        "formaat": self.eigenschap["specificatie"]["formaat"],
                        "waarde": self.zaakeigenschap.waarde,
                        "eigenschap": {
                            "url": self.eigenschap["url"],
                            "naam": self.eigenschap["naam"],
                            "toelichting": self.eigenschap["toelichting"],
                            "specificatie": self.eigenschap["specificatie"],
                        },
                    }
                ],
                "zaakDocuments": [],
                "approvals": [],
            },
        )

    def test_success_get_advice_review_request(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        mock_resource_get(m, self.zaak_json)
        rr = factory_review_request(self.review_request)
        rr.fetched_reviews = True
        rr.reviews = []

        self.client.force_authenticate(user=self.user)
        url = self.approval_url + f"?assignee={AssigneeTypeChoices.user}:{self.user}"

        with patch(
            "zac.contrib.objects.kownsl.api.views.get_review_request", return_value=rr
        ):
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "created": self.review_request["created"],
                "documents": [],
                "id": self.review_request["id"],
                "isBeingReconfigured": self.review_request["isBeingReconfigured"],
                "locked": self.review_request["locked"],
                "lockReason": self.review_request["lockReason"],
                "openReviews": [
                    {
                        "deadline": "2022-04-14",
                        "groups": [],
                        "users": ["Some First Some Last"],
                    },
                    {
                        "deadline": "2022-04-15",
                        "groups": [],
                        "users": ["Some Other First Some Last"],
                    },
                ],
                "requester": self.review_request["requester"],
                "reviewType": KownslTypes.advice,
                "toelichting": self.review_request["toelichting"],
                "zaak": {
                    "identificatie": self.zaak.identificatie,
                    "bronorganisatie": self.zaak.bronorganisatie,
                    "url": self.zaak.url,
                },
                "zaakeigenschappen": [],
                "zaakDocuments": [],
                "advices": [],
            },
        )

    def test_success_create_approval_review_request(self, m):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        m.get(
            f"{CAMUNDA_URL}task?processInstanceId={self.review_request['metadata']['processInstanceId']}&taskDefinitionKey={self.review_request['metadata']['taskDefinitionId']}&assignee={AssigneeTypeChoices.user}:{self.user}",
            json=[self.task],
        )
        mock_resource_get(m, self.zaak_json)
        _rr = deepcopy(self.review_request)
        _rr["documents"] = [self.document.url]

        rr = factory_review_request(_rr)
        rr.fetched_reviews = True
        rr.reviews = []
        rr.review_type = KownslTypes.approval

        self.client.force_authenticate(user=self.user)
        url = self.approval_url + f"?assignee={AssigneeTypeChoices.user}:{self.user}"

        payload = {
            "approved": True,
            "toelichting": "some toelichting here",
            "zaakeigenschappen": [
                {
                    "url": self.zaakeigenschap.url,
                    "naam": self.eigenschap["naam"],
                    "waarde": self.zaakeigenschap.waarde,
                }
            ],
        }
        approval = approval_factory()
        reviews = reviews_factory(reviews=[approval], reviewType=KownslTypes.approval)
        reviews_object = review_object_factory(record__data=reviews)
        with patch(
            "zac.contrib.objects.kownsl.api.views.get_review_request",
            return_value=rr,
        ), patch(
            "zac.contrib.objects.services.fetch_reviews", return_value=None
        ), patch(
            "zac.contrib.objects.services._create_unique_uuid_for_object",
            return_value=reviews["id"],
        ), patch(
            "zac.contrib.objects.services.create_meta_object_and_relate_to_zaak",
            return_value=reviews_object,
        ), patch(
            "zac.contrib.objects.kownsl.api.views.set_assignee_and_complete_task"
        ) as mock_set_assignee_and_complete_task, patch(
            "zac.contrib.objects.services.create_meta_object_and_relate_to_zaak",
            return_value=reviews_object,
        ) as mock_create_object:
            response = self.client.post(url, payload)

        self.assertEqual(response.status_code, 204)
        mock_set_assignee_and_complete_task.assert_called_once_with(
            factory(Task, self.task),
            f"{AssigneeTypeChoices.user}:{self.user}",
            variables={"author": f"{AssigneeTypeChoices.user}:{self.user}"},
        )
        mock_create_object.assert_called_once_with(
            "review",
            {
                "zaak": rr.zaak,
                "review_request": str(rr.id),
                "review_type": reviews["reviewType"],
                "reviews": [
                    {
                        "author": {
                            "email": self.user.email,
                            "first_name": self.user.first_name,
                            "full_name": f"{self.user.first_name} {self.user.last_name}",
                            "last_name": self.user.last_name,
                            "username": self.user.username,
                        },
                        "created": "2022-04-14T15:51:09.830235Z",
                        "approved": payload["approved"],
                        "review_documents": [
                            {
                                "document": self.document.url + "?versie=1",
                                "review_version": 1,
                                "source_version": 1,
                            }
                        ],
                        "group": None,
                        "toelichting": payload["toelichting"],
                        "zaakeigenschappen": [
                            {
                                "url": self.zaakeigenschap.url,
                                "naam": self.eigenschap["naam"],
                                "waarde": self.zaakeigenschap.waarde,
                            }
                        ],
                    }
                ],
                "id": reviews["id"],
                "requester": rr.requester,
            },
            rr.zaak,
        )

    def test_success_create_advice_review_request(self, m):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        m.get(
            f"{CAMUNDA_URL}task?processInstanceId={self.review_request['metadata']['processInstanceId']}&taskDefinitionKey={self.review_request['metadata']['taskDefinitionId']}&assignee={AssigneeTypeChoices.user}:{self.user}",
            json=[self.task],
        )
        mock_resource_get(m, self.zaak_json)
        rr = factory_review_request(self.review_request)
        rr.fetched_reviews = True
        rr.reviews = []
        rr.review_type = KownslTypes.advice

        self.client.force_authenticate(user=self.user)
        url = self.review_url + f"?assignee={AssigneeTypeChoices.user}:{self.user}"

        payload = {
            "advice": "some advice",
            "group": "",
            "reviewDocuments": [
                {
                    "document": self.document.url + "?versie=1",
                    "editedDocument": self.document.url + "?versie=2",
                }
            ],
            "zaakeigenschappen": [
                {
                    "url": self.zaakeigenschap.url,
                    "naam": self.eigenschap["naam"],
                    "waarde": self.zaakeigenschap.waarde,
                }
            ],
        }
        reviews_object = review_object_factory(record__data=self.reviews_advice)
        with patch(
            "zac.contrib.objects.kownsl.api.views.get_review_request",
            return_value=rr,
        ), patch(
            "zac.contrib.objects.services.fetch_reviews", return_value=None
        ), patch(
            "zac.contrib.objects.services._create_unique_uuid_for_object",
            return_value=self.reviews_advice["id"],
        ), patch(
            "zac.contrib.objects.services.create_meta_object_and_relate_to_zaak",
            return_value=reviews_object,
        ), patch(
            "zac.contrib.objects.kownsl.api.views.set_assignee_and_complete_task"
        ) as mock_set_assignee_and_complete_task, patch(
            "zac.contrib.objects.services.create_meta_object_and_relate_to_zaak",
            return_value=reviews_object,
        ) as mock_create_object:
            response = self.client.post(url, payload)

        mock_set_assignee_and_complete_task.assert_called_once_with(
            factory(Task, self.task),
            f"{AssigneeTypeChoices.user}:{self.user}",
            variables={"author": f"{AssigneeTypeChoices.user}:{self.user}"},
        )
        self.assertEqual(response.status_code, 204)
        mock_create_object.assert_called_once_with(
            "review",
            {
                "zaak": rr.zaak,
                "review_request": str(rr.id),
                "review_type": self.reviews_advice["reviewType"],
                "reviews": [
                    {
                        "advice": payload["advice"],
                        "author": {
                            "email": self.user.email,
                            "first_name": self.user.first_name,
                            "full_name": f"{self.user.first_name} {self.user.last_name}",
                            "last_name": self.user.last_name,
                            "username": self.user.username,
                        },
                        "created": "2022-04-14T15:51:09.830235Z",
                        "group": None,
                        "review_documents": [
                            {
                                "document": self.document.url + "?versie=1",
                                "review_version": 2,
                                "source_version": 1,
                            }
                        ],
                        "zaakeigenschappen": [
                            {
                                "url": self.zaakeigenschap.url,
                                "naam": self.eigenschap["naam"],
                                "waarde": self.zaakeigenschap.waarde,
                            }
                        ],
                    }
                ],
                "id": self.reviews_advice["id"],
                "requester": rr.requester,
            },
            rr.zaak,
        )

    def test_success_create_successive_advice_review_request(self, m):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        rr = factory_review_request(self.review_request)
        rr.fetched_reviews = True
        rr.reviews = factory_reviews(self.reviews_advice).reviews
        rr.review_type = KownslTypes.advice

        user = User.objects.get(
            username=rr.assigned_users[1].user_assignees[0]["username"]
        )
        self.client.force_authenticate(user=user)
        url = self.review_url + f"?assignee={AssigneeTypeChoices.user}:{user}"

        m.get(
            f"{CAMUNDA_URL}task?processInstanceId={self.review_request['metadata']['processInstanceId']}&taskDefinitionKey={self.review_request['metadata']['taskDefinitionId']}&assignee={AssigneeTypeChoices.user}:{user}",
            json=[self.task],
        )
        mock_resource_get(m, self.zaak_json)

        payload = {
            "advice": "some more advice",
            "group": "",
            "reviewDocuments": [
                {
                    "document": self.document.url + "?versie=2",
                    "editedDocument": self.document.url + "?versie=3",
                }
            ],
            "zaakeigenschappen": [
                {
                    "url": self.zaakeigenschap.url,
                    "naam": self.eigenschap["naam"],
                    "waarde": self.zaakeigenschap.waarde,
                }
            ],
        }
        reviews_object = review_object_factory(record__data=self.reviews_advice)
        with patch(
            "zac.contrib.objects.kownsl.api.views.get_review_request",
            return_value=rr,
        ), patch(
            "zac.contrib.objects.services.fetch_reviews",
            return_value=[reviews_object],
        ), patch(
            "zac.contrib.objects.services._create_unique_uuid_for_object",
            return_value="8fc50840-3450-4497-9d29-791113417023",
        ), patch(
            "zac.contrib.objects.services.update_object_record_data",
            return_value=reviews_object,
        ), patch(
            "zac.contrib.objects.kownsl.api.views.set_assignee_and_complete_task"
        ) as mock_set_assignee_and_complete_task, patch(
            "zac.contrib.objects.services.update_object_record_data",
            return_value=reviews_object,
        ) as mock_update_object:
            response = self.client.post(url, payload)

        mock_set_assignee_and_complete_task.assert_called_once_with(
            factory(Task, self.task),
            f"{AssigneeTypeChoices.user}:{user}",
            variables={"author": f"{AssigneeTypeChoices.user}:{user}"},
        )
        self.assertEqual(response.status_code, 204)
        mock_update_object.assert_called_once_with(
            {
                "url": reviews_object["url"],
                "uuid": reviews_object["uuid"],
                "type": reviews_object["type"],
                "record": {
                    "index": reviews_object["record"]["index"],
                    "typeVersion": reviews_object["record"]["typeVersion"],
                    "data": {
                        "id": self.reviews_advice["id"],
                        "reviews": [
                            {
                                "advice": self.reviews_advice["reviews"][0]["advice"],
                                "author": self.reviews_advice["reviews"][0]["author"],
                                "created": self.reviews_advice["reviews"][0]["created"],
                                "group": self.reviews_advice["reviews"][0]["group"],
                                "reviewDocuments": [
                                    {
                                        "document": self.document.url + "?versie=1",
                                        "reviewVersion": 2,
                                        "sourceVersion": 1,
                                    }
                                ],
                                "zaakeigenschappen": self.reviews_advice["reviews"][0][
                                    "zaakeigenschappen"
                                ],
                            },
                            {
                                "advice": payload["advice"],
                                "author": {
                                    "email": user.email,
                                    "firstName": user.first_name,
                                    "fullName": f"{user.first_name} {user.last_name}",
                                    "lastName": user.last_name,
                                    "username": user.username,
                                },
                                "created": "2022-04-14T15:51:09.830235Z",
                                "group": None,
                                "reviewDocuments": [
                                    {
                                        "document": self.document.url + "?versie=2",
                                        "reviewVersion": 3,
                                        "sourceVersion": 2,
                                    }
                                ],
                                "zaakeigenschappen": [
                                    {
                                        "url": self.zaakeigenschap.url,
                                        "naam": self.eigenschap["naam"],
                                        "waarde": self.zaakeigenschap.waarde,
                                    }
                                ],
                            },
                        ],
                        "requester": {
                            "email": self.user.email,
                            "username": self.user.username,
                            "firstName": self.user.first_name,
                            "lastName": self.user.last_name,
                            "fullName": f"{self.user.first_name} {self.user.last_name}",
                        },
                        "reviewRequest": str(rr.id),
                        "reviewType": rr.review_type,
                        "zaak": rr.zaak,
                    },
                    "geometry": reviews_object["record"]["geometry"],
                    "startAt": reviews_object["record"]["startAt"],
                    "endAt": reviews_object["record"]["endAt"],
                    "registrationAt": reviews_object["record"]["registrationAt"],
                    "correctionFor": reviews_object["record"]["correctionFor"],
                    "correctedBy": reviews_object["record"]["correctedBy"],
                },
            },
            {
                "id": self.reviews_advice["id"],
                "reviews": [
                    {
                        "advice": self.reviews_advice["reviews"][0]["advice"],
                        "author": self.reviews_advice["reviews"][0]["author"],
                        "created": self.reviews_advice["reviews"][0]["created"],
                        "group": self.reviews_advice["reviews"][0]["group"],
                        "reviewDocuments": [
                            {
                                "document": self.document.url + "?versie=1",
                                "reviewVersion": 2,
                                "sourceVersion": 1,
                            }
                        ],
                        "zaakeigenschappen": self.reviews_advice["reviews"][0][
                            "zaakeigenschappen"
                        ],
                    },
                    {
                        "advice": payload["advice"],
                        "author": {
                            "email": user.email,
                            "firstName": user.first_name,
                            "fullName": f"{user.first_name} {user.last_name}",
                            "lastName": user.last_name,
                            "username": user.username,
                        },
                        "created": "2022-04-14T15:51:09.830235Z",
                        "group": None,
                        "reviewDocuments": [
                            {
                                "document": self.document.url + "?versie=2",
                                "reviewVersion": 3,
                                "sourceVersion": 2,
                            }
                        ],
                        "zaakeigenschappen": [
                            {
                                "url": self.zaakeigenschap.url,
                                "naam": self.eigenschap["naam"],
                                "waarde": self.zaakeigenschap.waarde,
                            }
                        ],
                    },
                ],
                "reviewRequest": str(rr.id),
                "reviewType": rr.review_type,
                "requester": {
                    "email": self.user.email,
                    "username": self.user.username,
                    "firstName": self.user.first_name,
                    "lastName": self.user.last_name,
                    "fullName": f"{self.user.first_name} {self.user.last_name}",
                },
                "zaak": rr.zaak,
            },
        )
