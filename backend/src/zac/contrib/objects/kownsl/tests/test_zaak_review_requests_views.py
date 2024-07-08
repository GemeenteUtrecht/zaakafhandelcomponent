from copy import deepcopy
from os import path
from unittest.mock import patch

from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import Eigenschap, InformatieObjectType, ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.api_models.zaken import ZaakEigenschap
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import (
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.contrib.objects.kownsl.data import Advice, KownslTypes, ReviewRequest
from zac.contrib.objects.services import factory_reviews
from zac.core.permissions import zaken_inzien, zaken_wijzigen
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.api import create_informatieobject_document
from zac.tests.utils import mock_resource_get, paginated_response
from zgw.models.zrc import Zaak

from .factories import (
    CATALOGI_ROOT,
    DOCUMENT_URL,
    DOCUMENTS_ROOT,
    ZAAK_URL,
    ZAKEN_ROOT,
    advice_factory,
    kownsl_zaak_eigenschap_factory,
    review_document_factory,
    review_request_factory,
    reviews_factory,
)

CATALOGUS_URL = f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"


@requests_mock.Mocker()
class ZaakReviewRequestsResponseTests(ClearCachesMixin, APITestCase):
    """
    Test the API response body for zaak-review-requests endpoint.
    """

    @classmethod
    def setUpTestData(cls):
        cls.maxDiff = None
        super().setUpTestData()
        cls.user = SuperUserFactory.create()
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)

        # Mock ZRC/ZTC components
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
        cls.zaak = generate_oas_component(
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
            zaak=cls.zaak["url"],
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
        zaak = factory(Zaak, cls.zaak)
        zaak.zaaktype = factory(ZaakType, cls.zaaktype)
        zaakeigenschap = factory(ZaakEigenschap, cls.zaakeigenschap)
        zaakeigenschap.eigenschap = factory(Eigenschap, cls.eigenschap)

        # Mock DRC components
        document = factory(Document, cls.document)
        document.informatieobjecttype = factory(
            InformatieObjectType, cls.informatieobjecttype
        )
        document.last_edited_date = None  # avoid patching fetching audit trail

        # Create elasticsearch document
        es_document = create_informatieobject_document(document)

        # Mock kownsl components
        cls.review_request_dict = review_request_factory(
            documents=[deepcopy(DOCUMENT_URL)]
        )
        cls.review_request = factory(ReviewRequest, cls.review_request_dict)
        zei = kownsl_zaak_eigenschap_factory(
            url=zaakeigenschap.url,
            waarde=zaakeigenschap.waarde,
            naam=cls.eigenschap["naam"],
        )
        review_document = review_document_factory(
            document=es_document.url,
            sourceVersion=es_document.versie,
            reviewVersion=es_document.versie,
        )
        advice = advice_factory(
            zaakeigenschappen=[zei], reviewDocuments=[review_document]
        )
        cls.reviews = reviews_factory(reviews=[advice], reviewType=KownslTypes.advice)
        reviews = factory_reviews(cls.reviews)

        # Patchers
        cls.get_zaakeigenschappen_patcher = patch(
            "zac.contrib.objects.kownsl.data.get_zaakeigenschappen",
            return_value=[zaakeigenschap],
        )
        cls.find_zaak_patcher = patch("zac.core.api.views.find_zaak", return_value=zaak)
        cls.get_zaak_patcher = patch(
            "zac.contrib.objects.kownsl.api.views.get_zaak", return_value=zaak
        )
        cls.search_informatieobjects_patcher = patch(
            "zac.contrib.objects.kownsl.data.search_informatieobjects",
            return_value=[es_document],
        )
        cls.get_supported_extensions_patcher = patch(
            "zac.contrib.dowc.utils.get_supported_extensions",
            return_value=[path.splitext(es_document.bestandsnaam)],
        )
        cls.get_reviews_patcher = patch(
            "zac.contrib.objects.services.get_reviews_for_review_request",
            return_value=reviews,
        )
        cls.get_reviews_for_zaak_patcher = patch(
            "zac.contrib.objects.kownsl.api.views.get_reviews_for_zaak",
            return_value=[reviews],
        )
        cls.get_review_request_patcher = patch(
            "zac.contrib.objects.kownsl.api.views.get_review_request",
            return_value=cls.review_request,
        )
        cls.get_all_review_requests_for_zaak_patcher = patch(
            "zac.contrib.objects.kownsl.api.views.get_all_review_requests_for_zaak",
            return_value=[cls.review_request],
        )

        # set endpoints
        cls.endpoint_summary = reverse(
            "kownsl:zaak-review-requests-summary",
            kwargs={
                "bronorganisatie": "123456782",
                "identificatie": "ZAAK-2020-0010",
            },
        )
        cls.endpoint_detail = reverse(
            "kownsl:zaak-review-requests-detail",
            kwargs={
                "request_uuid": cls.review_request.id,
            },
        )

    def setUp(self):
        super().setUp()

        self.find_zaak_patcher.start()
        self.addCleanup(self.find_zaak_patcher.stop)

        self.get_all_review_requests_for_zaak_patcher.start()
        self.addCleanup(self.get_all_review_requests_for_zaak_patcher.stop)

        # ensure that we have a user with all permissions
        self.client.force_authenticate(user=self.user)

    def test_get_zaak_review_requests_completed(self, m):
        rr = review_request_factory()
        rr.update(
            {
                "locked": True,
                "lockReason": "Alle verzoeken zijn uitgevoerd.",
                "assignedUsers": [],
            }
        )
        with patch(
            "zac.contrib.objects.kownsl.api.views.get_all_review_requests_for_zaak",
            return_value=[factory(ReviewRequest, rr)],
        ):
            response = self.client.get(self.endpoint_summary)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(
            response_data,
            [
                {
                    "id": str(self.review_request.id),
                    "reviewType": KownslTypes.advice,
                    "completed": 0,
                    "numAssignedUsers": 0,
                    "canLock": False,
                    "locked": True,
                    "lockReason": "Alle verzoeken zijn uitgevoerd.",
                    "isBeingReconfigured": False,
                    "status": "completed",
                }
            ],
        )

    def test_get_zaak_review_requests_status_pending(self, m):
        response = self.client.get(self.endpoint_summary)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(
            response_data,
            [
                {
                    "id": str(self.review_request.id),
                    "reviewType": KownslTypes.advice,
                    "completed": 0,
                    "numAssignedUsers": 2,
                    "canLock": False,
                    "locked": False,
                    "lockReason": "",
                    "isBeingReconfigured": False,
                    "status": "pending",
                }
            ],
        )

    def test_get_zaak_review_requests_status_canceled(self, m):
        rr = review_request_factory()
        rr.update({"locked": True, "lockReason": "canceled by user"})
        with patch(
            "zac.contrib.objects.kownsl.api.views.get_all_review_requests_for_zaak",
            return_value=[factory(ReviewRequest, rr)],
        ):
            response = self.client.get(self.endpoint_summary)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(
            response_data,
            [
                {
                    "id": str(self.review_request.id),
                    "reviewType": KownslTypes.advice,
                    "completed": 0,
                    "numAssignedUsers": 2,
                    "canLock": False,
                    "locked": True,
                    "lockReason": "canceled by user",
                    "isBeingReconfigured": False,
                    "status": "canceled",
                }
            ],
        )

    def test_get_zaak_review_requests_can_lock(self, m):
        some_other_user = SuperUserFactory(
            username=self.review_request.requester["username"]
        )
        self.client.force_authenticate(user=some_other_user)
        response = self.client.get(self.endpoint_summary)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(
            response_data,
            [
                {
                    "id": str(self.review_request.id),
                    "reviewType": KownslTypes.advice,
                    "completed": 0,
                    "numAssignedUsers": 2,
                    "canLock": True,
                    "locked": False,
                    "lockReason": "",
                    "isBeingReconfigured": False,
                    "status": "pending",
                }
            ],
        )

    def test_get_zaak_review_requests_detail(self, m):
        rr = deepcopy(self.review_request)
        rr.zaakeigenschappen = [self.zaakeigenschap["url"]]
        with patch(
            "zac.contrib.objects.kownsl.api.views.get_review_request", return_value=rr
        ):
            with self.get_reviews_patcher:
                with self.get_zaak_patcher:
                    with self.search_informatieobjects_patcher:
                        with self.get_supported_extensions_patcher:
                            with self.get_zaakeigenschappen_patcher:
                                response = self.client.get(self.endpoint_detail)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(
            {
                "advices": [
                    {
                        "advice": self.reviews["reviews"][0]["advice"],
                        "author": self.reviews["reviews"][0]["author"],
                        "created": self.reviews["reviews"][0]["created"],
                        "group": {},
                        "reviewDocuments": [
                            {
                                "bestandsnaam": self.document["bestandsnaam"],
                                "document": self.document["url"],
                                "downloadReviewUrl": f"/core/documenten/{self.document['bronorganisatie']}/{self.document['identificatie']}/?versie=1",
                                "downloadSourceUrl": f"/core/documenten/{self.document['bronorganisatie']}/{self.document['identificatie']}/?versie=1",
                                "reviewUrl": "",
                                "reviewVersion": 1,
                                "sourceUrl": "",
                                "sourceVersion": 1,
                            }
                        ],
                        "zaakeigenschappen": [
                            {
                                "naam": self.eigenschap["naam"],
                                "url": self.zaakeigenschap["url"],
                                "waarde": self.zaakeigenschap["waarde"],
                            }
                        ],
                    }
                ],
                "created": self.review_request_dict["created"],
                "documents": [DOCUMENT_URL],
                "id": str(self.review_request.id),
                "isBeingReconfigured": False,
                "locked": False,
                "lockReason": "",
                "openReviews": [
                    {
                        "deadline": "2022-04-15",
                        "groups": [],
                        "users": ["Some Other First Some Last"],
                    }
                ],
                "requester": {
                    "email": "some-author@email.zac",
                    "firstName": "Some First",
                    "fullName": "Some First Some Last",
                    "lastName": "Some Last",
                    "username": "some-author",
                },
                "reviewType": self.review_request.review_type,
                "toelichting": self.review_request.toelichting,
                "zaak": {
                    "bronorganisatie": self.zaak["bronorganisatie"],
                    "identificatie": self.zaak["identificatie"],
                    "url": self.zaak["url"],
                },
                "zaakDocuments": [
                    {
                        "auteur": self.document["auteur"],
                        "beschrijving": self.document["beschrijving"],
                        "bestandsnaam": self.document["bestandsnaam"],
                        "bestandsomvang": self.document["bestandsomvang"],
                        "bronorganisatie": self.document["bronorganisatie"],
                        "currentUserIsEditing": False,
                        "deleteUrl": "",
                        "downloadUrl": "/core/documenten/123456782/DOC-2020-007/?versie=1",
                        "identificatie": self.document["identificatie"],
                        "informatieobjecttype": {
                            "url": self.informatieobjecttype["url"],
                            "omschrijving": self.informatieobjecttype["omschrijving"],
                        },
                        "lastEditedDate": None,
                        "locked": self.document["locked"],
                        "lockedBy": "",
                        "readUrl": "",
                        "relatedZaken": [],
                        "titel": self.document["titel"],
                        "url": self.document["url"],
                        "versie": 1,
                        "vertrouwelijkheidaanduiding": self.document[
                            "vertrouwelijkheidaanduiding"
                        ],
                        "writeUrl": "",
                    }
                ],
                "zaakeigenschappen": [
                    {
                        "eigenschap": {
                            "url": self.eigenschap["url"],
                            "naam": self.eigenschap["naam"],
                            "toelichting": self.eigenschap["toelichting"],
                            "specificatie": self.eigenschap["specificatie"],
                        },
                        "formaat": self.eigenschap["specificatie"]["formaat"],
                        "url": self.zaakeigenschap["url"],
                        "waarde": self.zaakeigenschap["waarde"],
                    }
                ],
            },
            response_data,
        )

    def test_no_review_request(self, m):
        with patch(
            "zac.contrib.objects.kownsl.api.views.get_review_request", return_value=None
        ):
            response = self.client.get(self.endpoint_detail)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_no_review_requests(self, m):
        with patch(
            "zac.contrib.objects.kownsl.api.views.get_all_review_requests_for_zaak",
            return_value=[],
        ):
            response = self.client.get(self.endpoint_summary)
        self.assertEqual(response.data, [])

    def test_find_zaak_not_found(self, m):
        with patch("zac.core.api.views.find_zaak", side_effect=ObjectDoesNotExist):
            response = self.client.get(self.endpoint_summary)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_review_request_lock(self, m):
        url = reverse(
            "kownsl:zaak-review-requests-detail",
            kwargs={"request_uuid": self.review_request.id},
        )
        body = {"lock_reason": "some-reason"}

        user = SuperUserFactory.create(
            username=self.review_request.requester["username"]
        )
        self.client.force_authenticate(user=user)
        rr = deepcopy(self.review_request)
        rr.locked = True
        with self.get_review_request_patcher:
            with self.get_reviews_patcher:
                with self.get_zaak_patcher:
                    with self.search_informatieobjects_patcher:
                        with self.get_supported_extensions_patcher:
                            with patch(
                                "zac.contrib.objects.kownsl.api.views.lock_review_request",
                                return_value=rr,
                            ) as patch_lock_review_request:
                                with patch(
                                    "zac.contrib.objects.kownsl.api.views.invalidate_review_requests_cache"
                                ) as patch_invalidate_cache:
                                    response = self.client.patch(url, body)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        patch_invalidate_cache.assert_called_once()
        patch_lock_review_request.assert_called_once()

    @patch("zac.contrib.objects.kownsl.api.views.send_message", return_value=None)
    def test_update_review_request_update_users(self, m, mock_send_message):
        url = reverse(
            "kownsl:zaak-review-requests-detail",
            kwargs={"request_uuid": self.review_request.id},
        )
        body = {"update_users": True}

        user = SuperUserFactory.create(
            username=self.review_request.requester["username"]
        )
        self.client.force_authenticate(user=user)
        with self.get_review_request_patcher:
            with self.get_reviews_patcher:
                with self.get_zaak_patcher:
                    with self.search_informatieobjects_patcher:
                        with self.get_supported_extensions_patcher:
                            with patch(
                                "zac.contrib.objects.kownsl.api.views.update_review_request",
                                return_value=self.review_request,
                            ) as patch_lock_review_request:
                                with patch(
                                    "zac.contrib.objects.kownsl.api.views.invalidate_review_requests_cache"
                                ) as patch_invalidate_cache:
                                    response = self.client.patch(url, body)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_message.assert_called_once_with(
            "change-process", [self.review_request.metadata["process_instance_id"]]
        )
        patch_invalidate_cache.assert_called_once()
        patch_lock_review_request.assert_called_once()

    def test_update_review_request_lock_and_update_users_fail(self, m):
        url = reverse(
            "kownsl:zaak-review-requests-detail",
            kwargs={"request_uuid": self.review_request.id},
        )
        body = {"lock_reason": "some-reason", "update_users": True}

        user = SuperUserFactory.create(
            username=self.review_request.requester["username"]
        )
        self.client.force_authenticate(user=user)
        rr = deepcopy(self.review_request)
        rr.locked = True
        with self.get_review_request_patcher:
            with self.get_reviews_patcher:
                with self.get_zaak_patcher:
                    with self.search_informatieobjects_patcher:
                        with self.get_supported_extensions_patcher:
                            response = self.client.patch(url, body)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "code": "invalid",
                    "name": "nonFieldErrors",
                    "reason": "Een verzoek die op slot staat kan niet worden bijgewerkt.",
                }
            ],
        )


class ZaakReviewRequestsPermissionTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=CATALOGUS_URL,
            domein="DOME",
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT1",
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            zaaktype=cls.zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            startdatum="2020-12-25",
            uiterlijkeEinddatumAfdoening="2021-01-04",
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
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            bestandsomvang=10,
        )

        zaak = factory(Zaak, cls.zaak)
        zaak.zaaktype = factory(ZaakType, cls.zaaktype)

        cls.find_zaak_patcher = patch("zac.core.api.views.find_zaak", return_value=zaak)
        cls.get_zaak_patcher = patch(
            "zac.contrib.objects.kownsl.permissions.get_zaak", return_value=zaak
        )

        cls.review_request = review_request_factory(documents=[])
        cls.review_request = factory(ReviewRequest, cls.review_request)
        cls.advices = factory(Advice, [advice_factory()])

        cls.endpoint_summary = reverse(
            "kownsl:zaak-review-requests-summary",
            kwargs={
                "bronorganisatie": "123456782",
                "identificatie": "ZAAK-2020-0010",
            },
        )
        cls.endpoint_detail = reverse(
            "kownsl:zaak-review-requests-detail",
            kwargs={
                "request_uuid": cls.review_request.id,
            },
        )

    def setUp(self):
        super().setUp()

        self.find_zaak_patcher.start()
        self.addCleanup(self.find_zaak_patcher.stop)

        self.get_zaak_patcher.start()
        self.addCleanup(self.get_zaak_patcher.stop)

    def test_rr_summary_not_authenticated(self):
        response = self.client.get(self.endpoint_summary)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_rr_detail_not_authenticated(self):
        response = self.client.get(self.endpoint_detail)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_get_rr_summary_authenticated_no_permissions(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([]),
        )
        user = UserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.get(self.endpoint_summary)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_rr_detail_authenticated_no_permissions(self):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.get(self.endpoint_detail)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_get_perm_but_not_for_zaaktype(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([]),
        )

        # gives them access to the page, but no catalogus specified -> nothing visible
        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=user,
            policy={
                "catalogus": "",
                "zaaktype_omschrijving": "",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )
        self.client.force_authenticate(user=user)

        with patch(
            "zac.contrib.objects.kownsl.api.views.get_all_review_requests_for_zaak",
            return_value=[self.review_request],
        ):
            response_summary = self.client.get(self.endpoint_summary)
        self.assertEqual(response_summary.status_code, status.HTTP_403_FORBIDDEN)

        with patch(
            "zac.contrib.objects.kownsl.api.views.get_review_request",
            return_value=self.review_request,
        ):
            response_detail = self.client.get(self.endpoint_detail)
        self.assertEqual(response_detail.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_get_perm_but_not_for_va(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        mock_resource_get(m, self.catalogus)
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([]),
        )
        user = UserFactory.create()
        # gives them access to the page and zaaktype, but insufficient VA
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )
        self.client.force_authenticate(user=user)

        with patch(
            "zac.contrib.objects.kownsl.api.views.get_all_review_requests_for_zaak",
            return_value=[self.review_request],
        ):
            response_summary = self.client.get(self.endpoint_summary)
        self.assertEqual(response_summary.status_code, status.HTTP_403_FORBIDDEN)

        with patch(
            "zac.contrib.objects.kownsl.api.views.get_review_request",
            return_value=self.review_request,
        ):
            response_detail = self.client.get(self.endpoint_detail)
        self.assertEqual(response_detail.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_zaak_not_found(self):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        with patch(
            "zac.contrib.objects.kownsl.api.views.get_review_request",
            return_value=self.review_request,
        ):
            with patch(
                "zac.contrib.objects.kownsl.permissions.get_zaak",
                side_effect=ObjectDoesNotExist,
            ):
                response = self.client.get(self.endpoint_detail)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @requests_mock.Mocker()
    def test_has_get_perm(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaak)

        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )

        user = UserFactory.create()
        # gives them access to the page, zaaktype and VA specified -> visible
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self.client.force_authenticate(user=user)

        with patch(
            "zac.contrib.objects.kownsl.api.views.get_all_review_requests_for_zaak",
            return_value=[self.review_request],
        ):
            response_summary = self.client.get(self.endpoint_summary)
        self.assertEqual(response_summary.status_code, status.HTTP_200_OK)

        with patch(
            "zac.contrib.objects.kownsl.api.views.get_review_request",
            return_value=self.review_request,
        ):
            response_detail = self.client.get(self.endpoint_detail)
        self.assertEqual(response_detail.status_code, status.HTTP_200_OK)

    @requests_mock.Mocker()
    def test_has_lock_perm(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaak)
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        user = UserFactory.create(username=self.review_request.requester["username"])
        # gives them access to the page, zaaktype and VA specified -> visible
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_wijzigen.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        self.client.force_authenticate(user=user)

        with patch(
            "zac.contrib.objects.kownsl.api.views.get_review_request",
            return_value=self.review_request,
        ):
            with patch(
                "zac.contrib.objects.kownsl.api.views.lock_review_request",
                return_value=self.review_request,
            ):
                response_detail = self.client.patch(
                    self.endpoint_detail, {"lock_reason": "zomaar"}
                )
        self.assertEqual(response_detail.status_code, status.HTTP_200_OK)

    @requests_mock.Mocker()
    def test_review_request_is_locked(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)

        user = UserFactory.create(username=self.review_request.requester["username"])
        self.client.force_authenticate(user=user)
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_wijzigen.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        with patch(
            "zac.contrib.objects.kownsl.api.views.get_review_request",
            return_value=factory(ReviewRequest, review_request_factory(locked=True)),
        ):
            response = self.client.patch(self.endpoint_detail, {"update_users": True})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.json()["detail"],
            "Verzoek is op slot gezet door `Some First Some Last`.",
        )

    @requests_mock.Mocker()
    def test_review_request_is_being_reconfigured(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)

        user = UserFactory.create(username=self.review_request.requester["username"])
        self.client.force_authenticate(user=user)
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_wijzigen.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        with patch(
            "zac.contrib.objects.kownsl.api.views.get_review_request",
            return_value=factory(
                ReviewRequest,
                review_request_factory(isBeingReconfigured=True, locked=False),
            ),
        ):
            response = self.client.patch(self.endpoint_detail, {"update_users": True})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()["detail"], "Dit verzoek wordt bijgewerkt.")

    @requests_mock.Mocker()
    def test_review_request_locked_get_regression(self, m):
        """
        Regression test to make sure users can still GET
        locked review requests.

        """
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaak)

        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        user = UserFactory.create(username=self.review_request.requester["username"])
        # gives them access to the page, zaaktype and VA specified -> visible
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self.client.force_authenticate(user=user)
        rr = deepcopy(self.review_request)
        rr.locked = True
        rr.lock_reason = "zomaar"
        with patch(
            "zac.contrib.objects.kownsl.api.views.get_review_request",
            return_value=rr,
        ):
            response_detail = self.client.get(self.endpoint_detail)
        self.assertEqual(response_detail.status_code, status.HTTP_200_OK)
