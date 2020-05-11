from django.conf import settings
from django.db import transaction
from django.urls import reverse_lazy

import requests_mock
from django_webtest import WebTest
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.accounts.tests.factories import PermissionSetFactory, UserFactory
from zac.tests.utils import (
    generate_oas_component,
    mock_service_oas_get,
    paginated_response,
)

from ..permissions import zaken_close, zaken_set_result
from .utils import ClearCachesMixin

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"

BRONORGANISATIE = "123456782"
IDENTIFICATIE = "ZAAK-001"


@requests_mock.Mocker()
class ZaakAfhandelingGETTests(ClearCachesMixin, WebTest):
    """
    Permission tests to get to the zaakafhandeling page.
    """

    url = reverse_lazy(
        "core:zaak-afhandeling",
        kwargs={"bronorganisatie": BRONORGANISATIE, "identificatie": IDENTIFICATIE,},
    )

    def setUp(self):
        super().setUp()

        self.user = UserFactory.create()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

    def _setUpMocks(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            catalogus=f"{CATALOGI_ROOT}catalogi/dfb14eb7-9731-4d22-95c2-dff4f33ef36d",
            identificatie="ZT1",
        )
        resultaattype = generate_oas_component(
            "ztc",
            "schemas/ResultaatType",
            url=f"{CATALOGI_ROOT}resultaattypen/ee512886-d0d9-4c12-9bbb-78b0d22bfb61",
            zaaktype=zaaktype["url"],
        )
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/05b2c190-b1f6-4767-9e35-38bcf7702968",
            bronorganisatie=BRONORGANISATIE,
            identificatie=IDENTIFICATIE,
            zaaktype=zaaktype["url"],
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={zaaktype['catalogus']}",
            json=paginated_response([zaaktype]),
        )
        m.get(
            f"{CATALOGI_ROOT}resultaattypen?zaaktype={zaaktype['url']}",
            json=paginated_response([resultaattype]),
        )
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie={BRONORGANISATIE}&identificatie={IDENTIFICATIE}",
            json=paginated_response([zaak]),
        )
        m.get(zaaktype["url"], json=zaaktype)

        self.zaaktype = zaaktype
        self.resultaattype = resultaattype
        self.zaak = zaak

    def test_login_required(self, m):
        response = self.app.get(self.url)

        self.assertRedirects(response, f"{settings.LOGIN_URL}?next={self.url}")

    def test_logged_in_no_permission_at_all(self, m):
        response = self.app.get(self.url, user=self.user, status=403)

        self.assertEqual(response.status_code, 403)

    def test_logged_in_either_permission_no_object_perm(self, m):
        permissions = [zaken_close, zaken_set_result]
        for permission in permissions:
            with self.subTest(permission=permission):
                sid = transaction.savepoint()

                # gives them access to the page, but no catalogus specified -> nothing visible
                PermissionSetFactory.create(
                    permissions=[permission.name],
                    for_user=self.user,
                    catalogus="",
                    zaaktype_identificaties=[],
                    max_va=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
                )

                response = self.app.get(self.url, user=self.user, status=403)

                # object level permission check should fail
                self.assertEqual(response.status_code, 403)
                self.assertEqual(m.call_count, 0)

                transaction.savepoint_rollback(sid)

    def test_logged_in_either_permission_all_zaaktypen_ok(self, m):
        self._setUpMocks(m)

        permissions = [zaken_close, zaken_set_result]
        for permission in permissions:
            with self.subTest(permission=permission):
                sid = transaction.savepoint()

                PermissionSetFactory.create(
                    permissions=[permission.name],
                    for_user=self.user,
                    catalogus=self.zaaktype["catalogus"],
                    zaaktype_identificaties=[],
                    max_va=VertrouwelijkheidsAanduidingen.zeer_geheim,
                )

                response = self.app.get(self.url, user=self.user)

                # object level permission check should fail
                self.assertEqual(response.status_code, 200)
                self.assertGreater(m.call_count, 0)

                transaction.savepoint_rollback(sid)

    def test_logged_in_both_permissions_all_zaaktypen_ok(self, m):
        self._setUpMocks(m)

        PermissionSetFactory.create(
            permissions=[zaken_close.name, zaken_set_result.name],
            for_user=self.user,
            catalogus=self.zaaktype["catalogus"],
            zaaktype_identificaties=[],
            max_va=VertrouwelijkheidsAanduidingen.zeer_geheim,
        )

        response = self.app.get(self.url, user=self.user)

        # object level permission check should fail
        self.assertEqual(response.status_code, 200)
        self.assertGreater(m.call_count, 0)

    def test_logged_in_permission_different_zaaktype(self, m):
        self._setUpMocks(m)

        permissions = [zaken_close, zaken_set_result]
        for permission in permissions:
            with self.subTest(permission=permission):
                sid = transaction.savepoint()

                PermissionSetFactory.create(
                    permissions=[permission.name],
                    for_user=self.user,
                    catalogus=self.zaaktype["catalogus"],
                    zaaktype_identificaties=["ZT2"],
                    max_va=VertrouwelijkheidsAanduidingen.zeer_geheim,
                )

                response = self.app.get(self.url, user=self.user, status=403)

                # object level permission check should fail
                self.assertEqual(response.status_code, 403)
                self.assertGreater(m.call_count, 0)

                transaction.savepoint_rollback(sid)

    def test_logged_in_permission_va_insufficient(self, m):
        self._setUpMocks(m)

        self.zaak[
            "vertrouwelijkheidaanduiding"
        ] = VertrouwelijkheidsAanduidingen.beperkt_openbaar

        permissions = [zaken_close, zaken_set_result]
        for permission in permissions:
            with self.subTest(permission=permission):
                sid = transaction.savepoint()

                PermissionSetFactory.create(
                    permissions=[permission.name],
                    for_user=self.user,
                    catalogus=self.zaaktype["catalogus"],
                    zaaktype_identificaties=["ZT1"],
                    max_va=VertrouwelijkheidsAanduidingen.openbaar,
                )

                response = self.app.get(self.url, user=self.user, status=403)

                # object level permission check should fail
                self.assertEqual(response.status_code, 403)
                self.assertGreater(m.call_count, 0)

                transaction.savepoint_rollback(sid)
