from unittest.mock import patch

from django.http import Http404
from django.urls import reverse

import requests_mock
from django_camunda.models import CamundaConfig
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import (
    AtomicPermissionFactory,
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.contrib.kownsl.data import ReviewRequest
from zac.contrib.kownsl.models import KownslConfig
from zac.core.permissions import zaken_wijzigen
from zac.core.tests.utils import ClearCachesMixin
from zgw.models.zrc import Zaak

from .utils import (
    CATALOGI_ROOT,
    DOCUMENTS_ROOT,
    KOWNSL_ROOT,
    REVIEW_REQUEST,
    ZAAK_URL,
    ZAKEN_ROOT,
)

CAMUNDA_ROOT = "https://some.camunda.nl/"
CAMUNDA_API_PATH = "engine-rest/"
CAMUNDA_URL = f"{CAMUNDA_ROOT}{CAMUNDA_API_PATH}"


@requests_mock.Mocker()
class ZaakReviewRequestsReminderResponseTests(APITestCase):
    """
    Test the API response body for zaak-review-request-reminder endpoint.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = SuperUserFactory.create()
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        kownsl_service = Service.objects.create(
            label="kownsl",
            api_type=APITypes.orc,
            api_root=KOWNSL_ROOT,
            auth_type=AuthTypes.zgw,
            client_id="zac",
            secret="supersecret",
            user_id="zac",
        )

        config = KownslConfig.get_solo()
        config.service = kownsl_service
        config.save()

        config = CamundaConfig.get_solo()
        config.root_url = CAMUNDA_ROOT
        config.rest_api_path = CAMUNDA_API_PATH
        config.save()
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            startdatum="2020-12-25",
            uiterlijkeEinddatumAfdoening="2021-01-04",
        )

        zaak = factory(Zaak, cls.zaak)
        cls.get_zaak_patcher = patch(
            "zac.contrib.kownsl.views.get_zaak", return_value=zaak
        )
        # Let resolve_assignee get the right users and groups
        UserFactory.create(
            username=REVIEW_REQUEST["assignedUsers"][0]["user_assignees"][0]
        )
        UserFactory.create(
            username=REVIEW_REQUEST["assignedUsers"][1]["user_assignees"][0]
        )
        review_request = factory(ReviewRequest, REVIEW_REQUEST)
        cls.get_review_request_patcher = patch(
            "zac.contrib.kownsl.views.get_review_request", return_value=review_request
        )
        cls.get_advices_patcher = patch(
            "zac.contrib.kownsl.views.retrieve_advices", return_value=[]
        )
        cls.get_approvals_patcher = patch(
            "zac.contrib.kownsl.views.retrieve_approvals", return_value=[]
        )
        cls.endpoint = reverse(
            "kownsl:zaak-review-requests-reminder",
            kwargs={
                "request_uuid": review_request.id,
            },
        )

    def setUp(self):
        super().setUp()
        self.get_zaak_patcher.start()
        self.addCleanup(self.get_zaak_patcher.stop)

        self.get_review_request_patcher.start()
        self.addCleanup(self.get_review_request_patcher.stop)

        self.get_advices_patcher.start()
        self.addCleanup(self.get_advices_patcher.stop)

        self.get_approvals_patcher.start()
        self.addCleanup(self.get_approvals_patcher.stop)

        # ensure that we have a user with all permissions
        self.client.force_authenticate(user=self.superuser)

    def test_post_zaak_review_request_reminder(self, m):
        m.post(f"{CAMUNDA_URL}message", status_code=status.HTTP_204_NO_CONTENT)
        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, 204)

    def test_get_zaak_review_request_is_locked(self, m):
        rr = factory(
            ReviewRequest,
            {**REVIEW_REQUEST, "locked": True, "lockReason": "just a reason"},
        )
        with patch(
            "zac.contrib.kownsl.views.get_review_request",
            return_value=rr,
        ):
            response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_zaak_review_request_not_found(self, m):
        rr = factory(
            ReviewRequest,
            {**REVIEW_REQUEST, "locked": True, "lockReason": "just a reason"},
        )
        with patch(
            "zac.contrib.kownsl.views.get_review_request",
            side_effect=Http404,
        ):
            response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ZaakReviewRequestsReminderPermissionsTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        cls.kownsl_service = Service.objects.create(
            label="Kownsl",
            api_type=APITypes.orc,
            api_root=KOWNSL_ROOT,
            auth_type=AuthTypes.zgw,
            client_id="zac",
            secret="supersecret",
            user_id="zac",
        )

        config = KownslConfig.get_solo()
        config.service = cls.kownsl_service
        config.save()
        config = CamundaConfig.get_solo()
        config.root_url = CAMUNDA_ROOT
        config.rest_api_path = CAMUNDA_API_PATH
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

        zaak = factory(Zaak, cls.zaak)
        zaak.zaaktype = factory(ZaakType, cls.zaaktype)

        cls.get_zaak_patcher = patch(
            "zac.contrib.kownsl.permissions.get_zaak", return_value=zaak
        )
        # Let resolve_assignee get the right users and groups
        UserFactory.create(
            username=REVIEW_REQUEST["assignedUsers"][0]["user_assignees"][0]
        )
        UserFactory.create(
            username=REVIEW_REQUEST["assignedUsers"][1]["user_assignees"][0]
        )
        cls.review_request = factory(ReviewRequest, REVIEW_REQUEST)
        cls.endpoint = reverse(
            "kownsl:zaak-review-requests-reminder",
            kwargs={
                "request_uuid": cls.review_request.id,
            },
        )

    def setUp(self):
        super().setUp()
        self.get_zaak_patcher.start()
        self.addCleanup(self.get_zaak_patcher.stop)

    def test_rr_reminder_not_authenticated(self):
        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_rr_reminder_authenticated_no_permissions(self, m):
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests/{REVIEW_REQUEST['id']}",
            json=REVIEW_REQUEST,
        )
        user = UserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_perm_but_not_for_zaaktype(self, m):
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests/{REVIEW_REQUEST['id']}",
            json=REVIEW_REQUEST,
        )
        # gives them access to the page, but no catalogus specified -> nothing visible
        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_wijzigen.name],
            for_user=user,
            policy={
                "catalogus": "",
                "zaaktype_omschrijving": "",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )
        self.client.force_authenticate(user=user)
        response_summary = self.client.post(self.endpoint)
        self.assertEqual(response_summary.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_perm_but_not_for_va(self, m):
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests/{REVIEW_REQUEST['id']}",
            json=REVIEW_REQUEST,
        )
        # gives them access to the page, but VA too low -> nothing visible
        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_wijzigen.name],
            for_user=user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )
        self.client.force_authenticate(user=user)
        response_summary = self.client.post(self.endpoint)
        self.assertEqual(response_summary.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_blueprint_perm(self, m):
        m.post(f"{CAMUNDA_URL}message", status_code=status.HTTP_204_NO_CONTENT)
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests/{REVIEW_REQUEST['id']}",
            json=REVIEW_REQUEST,
        )
        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_wijzigen.name],
            for_user=user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.geheim,
            },
        )
        self.client.force_authenticate(user=user)
        response_summary = self.client.post(self.endpoint)
        self.assertEqual(response_summary.status_code, status.HTTP_204_NO_CONTENT)

    @requests_mock.Mocker()
    def test_has_atomic_perm(self, m):
        m.post(f"{CAMUNDA_URL}message", status_code=status.HTTP_204_NO_CONTENT)
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests/{REVIEW_REQUEST['id']}",
            json=REVIEW_REQUEST,
        )
        user = UserFactory.create()
        AtomicPermissionFactory.create(
            object_url=ZAAK_URL,
            permission=zaken_wijzigen.name,
            for_user=user,
        )
        self.client.force_authenticate(user=user)
        response_summary = self.client.post(self.endpoint)
        self.assertEqual(response_summary.status_code, status.HTTP_204_NO_CONTENT)
