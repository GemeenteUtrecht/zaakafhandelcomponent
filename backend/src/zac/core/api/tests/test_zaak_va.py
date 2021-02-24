
from django.urls import reverse

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import (
    PermissionSetFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.core.permissions import zaken_inzien
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import mock_resource_get, paginated_response

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"


@requests_mock.Mocker()
class ChangeCaseVAResponseTests(ClearCachesMixin, APITestCase):
    """
    Test the changing of the case confidentiality level.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()

        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
        )

        cls.endpoint = reverse(
            "change-case-confidentiality",
        )

    def setUp(self):
        super().setUp()
        # ensure that we have a user with all permissions
        self.client.force_authenticate(user=self.user)

    def test_change_va(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)

        m.patch(self.zaak["url"], status_code=status.HTTP_200_OK)

        response = self.client.patch(
            self.endpoint,
            {
                "zaakUrl": self.zaak["url"],
                "vertrouwelijkheidsaanduiding": VertrouwelijkheidsAanduidingen.zeer_geheim,
                "reden": "because",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(m.last_request.url, self.zaak["url"])
        self.assertEqual(
            m.last_request.json(),
            {
                "vertrouwelijkheidsaanduiding": VertrouwelijkheidsAanduidingen.zeer_geheim
            },
        )

    def test_change__va_invalid(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)

        m.patch(self.zaak["url"], status_code=status.HTTP_200_OK)

        response = self.client.patch(
            self.endpoint,
            {
                "zaakUrl": self.zaak["url"],
                "vertrouwelijkheidsaanduiding": "zo-geheim-dit",
                "reden": "because",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {
                "vertrouwelijkheidsaanduiding": [
                    '"zo-geheim-dit" is een ongeldige keuze.'
                ]
            },
        )


class ChangeCaseVAPermissionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

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

        cls.endpoint = reverse(
            "change-case-confidentiality",
        )

    def test_not_authenticated(self):
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_no_permissions(self):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_perm(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        mock_resource_get(m, self.zaak)
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

        m.patch(self.zaak["url"], status_code=status.HTTP_200_OK)
        response = self.client.patch(
            self.endpoint,
            {
                "zaakUrl": self.zaak["url"],
                "vertrouwelijkheidsaanduiding": VertrouwelijkheidsAanduidingen.zeer_geheim,
                "reden": "because",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
