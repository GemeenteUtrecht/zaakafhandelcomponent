import uuid
from unittest.mock import patch

from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zds_client.client import ClientError
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import (
    PermissionSetFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.contrib.kownsl.api import get_client
from zac.contrib.kownsl.data import Advice, KownslTypes, ReviewRequest
from zac.contrib.kownsl.models import KownslConfig
from zac.core.permissions import zaken_inzien
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import paginated_response
from zgw.models.zrc import Zaak

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"
DOCUMENTS_ROOT = "http://documents.nl/api/v1/"


@requests_mock.Mocker()
class ZaakReviewRequestsResponseTests(APITestCase):
    """
    Test the API response body for zaak-review-requests endpoint.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        cls.kownsl_service = Service.objects.create(
            label="Kownsl",
            api_type=APITypes.orc,
            api_root="https://kownsl.nl",
            auth_type=AuthTypes.zgw,
            client_id="zac",
            secret="supersecret",
            oas="https://kownsl.nl/api/v1",
            user_id="zac",
        )

        config = KownslConfig.get_solo()
        config.service = cls.kownsl_service
        config.save()

        catalogus_url = (
            f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            zaaktype=cls.zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            startdatum="2020-12-25",
            uiterlijkeEinddatumAfdoening="2021-01-04",
        )
        cls.documenttype = generate_oas_component(
            "ztc",
            "schemas/InformatieObjectType",
            url=f"{CATALOGI_ROOT}informatieobjecttypen/d5d7285d-ce95-4f9e-a36f-181f1c642aa6",
            omschrijving="bijlage",
            catalogus=catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )
        cls.document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b6",
            identificatie="DOC-2020-007",
            bronorganisatie="123456782",
            informatieobjecttype=cls.documenttype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            bestandsomvang=10,
        )

        zaak = factory(Zaak, cls.zaak)
        zaak.zaaktype = factory(ZaakType, cls.zaaktype)

        cls.find_zaak_patcher = patch("zac.core.api.views.find_zaak", return_value=zaak)
        cls.get_zaak_patcher = patch(
            "zac.contrib.kownsl.views.get_zaak", return_value=zaak
        )

        # can't use generate_oas_component because Kownsl API schema doesn't have components
        # so manually creating review request, author, advicedocument, advice
        cls._uuid = uuid.uuid4()
        review_request = {
            "id": cls._uuid,
            "created": "2021-01-07T12:00:00Z",
            "forZaak": zaak.url,
            "reviewType": KownslTypes.advice,
            "documents": [cls.document["url"]],
            "frontendUrl": "http://some-kownsl-url.com/frontend-stuff",
            "numAdvices": 1,
            "numApprovals": 0,
            "numAssignedUsers": 2,
            "toelichting": "",
            "userDeadlines": {"some-user": "2021-01-07", "some-user-2": "2021-01-08"},
            "requester": "some-other-user",
        }
        review_request = factory(ReviewRequest, review_request)

        cls.get_review_request_patcher = patch(
            "zac.contrib.kownsl.views.get_review_request", return_value=review_request
        )

        cls.get_review_requests_patcher = patch(
            "zac.contrib.kownsl.views.get_review_requests",
            return_value=[review_request],
        )

        advice_document = {
            "document": cls.document["url"],
            "sourceVersion": 1,
            "adviceVersion": 1,
        }

        author = {
            "username": cls.user.username,
            "firstName": "some-first-name",
            "lastName": "some-last-name",
        }

        advices = [
            {
                "created": "2021-01-07T12:00:00Z",
                "author": author,
                "advice": "some-advice",
                "documents": [advice_document],
            },
        ]
        advices = factory(Advice, advices)

        cls.get_advices_patcher = patch(
            "zac.contrib.kownsl.views.retrieve_advices", return_value=advices
        )
        cls.get_approvals_patcher = patch(
            "zac.contrib.kownsl.views.retrieve_approvals", return_value=[]
        )

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
                "request_uuid": review_request.id,
            },
        )

    def setUp(self):
        super().setUp()

        self.find_zaak_patcher.start()
        self.addCleanup(self.find_zaak_patcher.stop)

        self.get_zaak_patcher.start()
        self.addCleanup(self.get_zaak_patcher.stop)

        self.get_review_requests_patcher.start()
        self.addCleanup(self.get_review_requests_patcher.stop)

        self.get_advices_patcher.start()
        self.addCleanup(self.get_advices_patcher.stop)

        self.get_approvals_patcher.start()
        self.addCleanup(self.get_approvals_patcher.stop)

        # ensure that we have a user with all permissions
        self.client.force_authenticate(user=self.user)

    def test_get_zaak_review_requests_completed(self, m):
        response = self.client.get(self.endpoint_summary)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(
            response_data,
            [
                {
                    "id": str(self._uuid),
                    "reviewType": KownslTypes.advice,
                    "completed": 1,
                    "numAssignedUsers": 2,
                }
            ],
        )

    def test_get_zaak_review_requests_detail(self, m):
        self.get_review_request_patcher.start()
        response = self.client.get(self.endpoint_detail)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()

        self.assertEqual(
            response_data,
            {
                "id": str(self._uuid),
                "reviewType": KownslTypes.advice,
                "reviews": [
                    {
                        "created": "2021-01-07T12:00:00Z",
                        "author": {
                            "firstName": "some-first-name",
                            "lastName": "some-last-name",
                            "username": self.user.username,
                        },
                        "advice": "some-advice",
                        "documents": [
                            {
                                "document": self.document["url"],
                                "sourceVersion": 1,
                                "adviceVersion": 1,
                            }
                        ],
                    }
                ],
            },
        )
        self.get_review_request_patcher.stop()

    def test_no_review_request(self, m):
        mock_service_oas_get(
            m, self.kownsl_service.api_root, "kownsl", oas_url=self.kownsl_service.oas
        )

        kownsl_client = get_client()
        with patch.object(
            kownsl_client, "get_operation_url", return_value="", create=True
        ):
            with patch.object(
                kownsl_client, "request", side_effect=ClientError, create=True
            ):
                with patch(
                    "zac.contrib.kownsl.api.get_client", return_value=kownsl_client
                ):
                    response = self.client.get(self.endpoint_detail)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_zaak_not_found(self, m):
        self.get_review_request_patcher.start()
        with patch("zac.contrib.kownsl.views.get_zaak", side_effect=ObjectDoesNotExist):
            response = self.client.get(self.endpoint_detail)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.get_review_request_patcher.stop()

    def test_no_review_requests(self, m):
        with patch("zac.contrib.kownsl.views.get_review_requests", return_value=[]):
            response = self.client.get(self.endpoint_summary)
        self.assertEqual(response.data, [])

    def test_find_zaak_not_found(self, m):
        with patch("zac.core.api.views.find_zaak", side_effect=ObjectDoesNotExist):
            response = self.client.get(self.endpoint_summary)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ZaakReviewRequestsPermissionTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        cls.kownsl_service = Service.objects.create(
            label="Kownsl",
            api_type=APITypes.orc,
            api_root="https://kownsl.nl",
            auth_type=AuthTypes.zgw,
            client_id="zac",
            secret="supersecret",
            oas="https://kownsl.nl/api/v1",
            user_id="zac",
        )

        config = KownslConfig.get_solo()
        config.service = cls.kownsl_service
        config.save()

        catalogus_url = (
            f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            zaaktype=cls.zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            startdatum="2020-12-25",
            uiterlijkeEinddatumAfdoening="2021-01-04",
        )
        cls.documenttype = generate_oas_component(
            "ztc",
            "schemas/InformatieObjectType",
            url=f"{CATALOGI_ROOT}informatieobjecttypen/d5d7285d-ce95-4f9e-a36f-181f1c642aa6",
            omschrijving="bijlage",
            catalogus=catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )
        cls.document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b6",
            identificatie="DOC-2020-007",
            bronorganisatie="123456782",
            informatieobjecttype=cls.documenttype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            bestandsomvang=10,
        )

        zaak = factory(Zaak, cls.zaak)
        zaak.zaaktype = factory(ZaakType, cls.zaaktype)

        cls.find_zaak_patcher = patch("zac.core.api.views.find_zaak", return_value=zaak)
        cls.get_zaak_patcher = patch(
            "zac.contrib.kownsl.views.get_zaak", return_value=zaak
        )

        # can't use generate_oas_component because Kownsl API schema doesn't have components
        # so manually creating review request, author, advicedocument, advice
        cls._uuid = uuid.uuid4()
        cls.review_request_data = {
            "id": str(cls._uuid),
            "created": "2021-01-07T12:00:00Z",
            "forZaak": zaak.url,
            "reviewType": KownslTypes.advice,
            "documents": [cls.document["url"]],
            "frontendUrl": "http://some-kownsl-url.com/frontend-stuff",
            "numAdvices": 1,
            "numApprovals": 0,
            "numAssignedUsers": 2,
            "toelichting": "",
            "userDeadlines": {"some-user": "2021-01-07", "some-user-2": "2021-01-08"},
            "requester": "some-other-user",
        }
        cls.review_request = factory(ReviewRequest, cls.review_request_data)

        advice_document = {
            "document": cls.document["url"],
            "sourceVersion": 1,
            "adviceVersion": 1,
        }

        author = {
            "username": "some-user-name",
            "firstName": "some-first-name",
            "lastName": "some-last-name",
        }

        advices = [
            {
                "created": "2021-01-07T12:00:00Z",
                "author": author,
                "advice": "some-advice",
                "documents": [advice_document],
            },
        ]
        cls.advices = factory(Advice, advices)

        cls.get_advices_patcher = patch(
            "zac.contrib.kownsl.api.retrieve_advices", return_value=advices
        )
        cls.get_approvals_patcher = patch(
            "zac.contrib.kownsl.api.retrieve_approvals", return_value=[]
        )

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
                "request_uuid": cls.review_request_data["id"],
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

    def test_rr_summary_authenticated_no_permissions(self):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.get(self.endpoint_summary)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_rr_detail_authenticated_no_permissions(self):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.get(self.endpoint_detail)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_perm_but_not_for_zaaktype(self):
        # gives them access to the page, but no catalogus specified -> nothing visible
        user = UserFactory.create()
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=user,
            catalogus="",
            zaaktype_identificaties=[],
            max_va=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
        )
        self.client.force_authenticate(user=user)

        with patch(
            "zac.contrib.kownsl.views.get_review_requests",
            return_value=[self.review_request],
        ):
            response_summary = self.client.get(self.endpoint_summary)
        self.assertEqual(response_summary.status_code, status.HTTP_403_FORBIDDEN)

        with patch(
            "zac.contrib.kownsl.views.get_review_request",
            return_value=self.review_request,
        ):
            response_detail = self.client.get(self.endpoint_detail)
        self.assertEqual(response_detail.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_perm_but_not_for_va(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        user = UserFactory.create()
        # gives them access to the page and zaaktype, but insufficient VA
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=user,
            catalogus=self.zaaktype["catalogus"],
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.openbaar,
        )
        self.client.force_authenticate(user=user)

        with patch(
            "zac.contrib.kownsl.views.get_review_requests",
            return_value=[self.review_request],
        ):
            response_summary = self.client.get(self.endpoint_summary)
        self.assertEqual(response_summary.status_code, status.HTTP_403_FORBIDDEN)

        with patch(
            "zac.contrib.kownsl.views.get_review_request",
            return_value=self.review_request,
        ):
            response_detail = self.client.get(self.endpoint_detail)
        self.assertEqual(response_detail.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_perm(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        user = UserFactory.create()
        # gives them access to the page, zaaktype and VA specified -> visible
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=user,
            catalogus=self.zaaktype["catalogus"],
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
        )
        self.client.force_authenticate(user=user)

        with patch(
            "zac.contrib.kownsl.views.get_review_requests",
            return_value=[self.review_request],
        ):
            response_summary = self.client.get(self.endpoint_summary)
        self.assertEqual(response_summary.status_code, status.HTTP_200_OK)

        with patch(
            "zac.contrib.kownsl.views.get_review_request",
            return_value=self.review_request,
        ):
            with patch(
                "zac.contrib.kownsl.views.retrieve_advices", return_value=self.advices
            ):
                with patch(
                    "zac.contrib.kownsl.views.retrieve_approvals", return_value=[]
                ):
                    response_detail = self.client.get(self.endpoint_detail)
        self.assertEqual(response_detail.status_code, status.HTTP_200_OK)
