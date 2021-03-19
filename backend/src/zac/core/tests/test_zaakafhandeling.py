from unittest import skip
from unittest.mock import patch

from django.conf import settings
from django.db import transaction
from django.urls import reverse_lazy

import requests_mock
from django_webtest import WebTest
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import PermissionDefinitionFactory, UserFactory
from zac.contrib.kownsl.models import KownslConfig
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.utils import paginated_response

from ..permissions import zaken_close, zaken_set_result
from .utils import ClearCachesMixin

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"
KOWNSL_ROOT = "https://kownsl.nl/"

BRONORGANISATIE = "123456782"
IDENTIFICATIE = "ZAAK-001"


@requests_mock.Mocker()
class ZaakAfhandelingGETTests(ESMixin, ClearCachesMixin, WebTest):
    """
    Permission tests to get to the zaakafhandeling page.
    """

    url = reverse_lazy(
        "core:zaak-afhandeling",
        kwargs={"bronorganisatie": BRONORGANISATIE, "identificatie": IDENTIFICATIE},
    )

    def setUp(self):
        super().setUp()

        self.user = UserFactory.create()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        kownsl = Service.objects.create(api_type=APITypes.orc, api_root=KOWNSL_ROOT)

        config = KownslConfig.get_solo()
        config.service = kownsl
        config.save()

        mock_allowlist = patch("zac.core.rules.test_oo_allowlist", return_value=True)
        mock_allowlist.start()
        self.addCleanup(mock_allowlist.stop)

    def _setUpMocks(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            catalogus=f"{CATALOGI_ROOT}catalogi/dfb14eb7-9731-4d22-95c2-dff4f33ef36d",
            identificatie="ZT1",
            omschrijving="ZT1",
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
        self._setUpMocks(m)
        permissions = [zaken_close, zaken_set_result]
        for permission in permissions:
            with self.subTest(permission=permission):
                sid = transaction.savepoint()

                # gives them access to the page, but no catalogus specified -> nothing visible
                PermissionDefinitionFactory.create(
                    object_url="",
                    permission=permission.name,
                    for_user=self.user,
                    policy={
                        "catalogus": "",
                        "zaaktype_omschrijving": "",
                        "max_va": VertrouwelijkheidsAanduidingen.openbaar,
                    },
                )

                response = self.app.get(self.url, user=self.user, status=403)

                # object level permission check should fail
                self.assertEqual(response.status_code, 403)

                transaction.savepoint_rollback(sid)

    @skip("Adding one permissions to all zaaktypen is deprecated")
    def test_logged_in_either_permission_all_zaaktypen_ok(self, m):
        self._setUpMocks(m)
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([]),
        )
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests?for_zaak={self.zaak['url']}",
            json=[],
        )

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

    @skip("Adding one permissions to all zaaktypen is deprecated")
    def test_logged_in_both_permissions_all_zaaktypen_ok(self, m):
        self._setUpMocks(m)
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([]),
        )
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests?for_zaak={self.zaak['url']}",
            json=[],
        )

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

                PermissionDefinitionFactory.create(
                    object_url="",
                    permission=permission.name,
                    for_user=self.user,
                    policy={
                        "catalogus": self.zaaktype["catalogus"],
                        "zaaktype_omschrijving": "ZT2",
                        "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
                    },
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

                PermissionDefinitionFactory.create(
                    object_url="",
                    permission=permission.name,
                    for_user=self.user,
                    policy={
                        "catalogus": self.zaaktype["catalogus"],
                        "zaaktype_omschrijving": "ZT1",
                        "max_va": VertrouwelijkheidsAanduidingen.openbaar,
                    },
                )

                response = self.app.get(self.url, user=self.user, status=403)

                # object level permission check should fail
                self.assertEqual(response.status_code, 403)
                self.assertGreater(m.call_count, 0)

                transaction.savepoint_rollback(sid)


@requests_mock.Mocker()
class ZaakAfhandelingPOSTTests(ESMixin, ClearCachesMixin, WebTest):
    """
    Permission tests for afhandel-form submission.
    """

    url = reverse_lazy(
        "core:zaak-afhandeling",
        kwargs={
            "bronorganisatie": BRONORGANISATIE,
            "identificatie": IDENTIFICATIE,
        },
    )

    def setUp(self):
        super().setUp()

        self.user = UserFactory.create()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

        mock_allowlist = patch("zac.core.rules.test_oo_allowlist", return_value=True)
        mock_allowlist.start()
        self.addCleanup(mock_allowlist.stop)

    def _setUpMocks(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            catalogus=f"{CATALOGI_ROOT}catalogi/dfb14eb7-9731-4d22-95c2-dff4f33ef36d",
            identificatie="ZT1",
            omschrijving="ZT1",
        )
        resultaattype = generate_oas_component(
            "ztc",
            "schemas/ResultaatType",
            url=f"{CATALOGI_ROOT}resultaattypen/ee512886-d0d9-4c12-9bbb-78b0d22bfb61",
            zaaktype=zaaktype["url"],
        )
        statustype = generate_oas_component(
            "ztc",
            "schemas/StatusType",
            url=f"{CATALOGI_ROOT}statustypen/f4e659c4-8b56-4596-beae-ee1353a3d95b",
            volgnummer=1,
            isEindstatus=True,
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
            f"{CATALOGI_ROOT}statustypen?zaaktype={zaaktype['url']}",
            json=paginated_response([statustype]),
        )
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie={BRONORGANISATIE}&identificatie={IDENTIFICATIE}",
            json=paginated_response([zaak]),
        )
        m.get(zaaktype["url"], json=zaaktype)

        resultaat = generate_oas_component(
            "zrc",
            "schemas/Resultaat",
            url=f"{ZAKEN_ROOT}resultaten/a11dd05c-e1c7-4b12-bf77-7e35790e1ce4",
            zaak=zaak["url"],
            resultaattype=resultaattype["url"],
        )
        m.post(f"{ZAKEN_ROOT}resultaten", status_code=201, json=resultaat)

        status = generate_oas_component(
            "zrc",
            "schemas/Status",
            url=f"{ZAKEN_ROOT}statussen/3bdc9329-3f19-4de0-ad6a-845d063611f4",
            zaak=zaak["url"],
            statustype=statustype["url"],
            # datumStatusGezet="2020-05-11T12:20:00Z",
        )
        m.post(f"{ZAKEN_ROOT}statussen", status_code=201, json=status)

        self.zaaktype = zaaktype
        self.resultaattype = resultaattype
        self.zaak = zaak

    def test_set_result_close_blocked(self, m):
        self._setUpMocks(m)
        PermissionDefinitionFactory.create(
            object_url="",
            permission=zaken_set_result.name,
            for_user=self.user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self.client.force_login(self.user)
        data = {
            "resultaattype": self.resultaattype["url"],
            "close_zaak": True,
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)

        # assert API calls -> closing zaak is forbidden, so we only expect a post for
        # resultaat creation
        post_requests = [req for req in m.request_history if req.method == "POST"]
        self.assertEqual(len(post_requests), 1)
        self.assertEqual(
            post_requests[0].url,
            f"{ZAKEN_ROOT}resultaten",
        )

    def test_close_set_result_blocked(self, m):
        self._setUpMocks(m)
        PermissionDefinitionFactory.create(
            object_url="",
            permission=zaken_close.name,
            for_user=self.user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self.client.force_login(self.user)
        data = {
            "resultaattype": self.resultaattype["url"],
            "close_zaak": True,
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)

        # assert API calls -> closing zaak is forbidden, so we only expect a post for
        # resultaat creation
        post_requests = [req for req in m.request_history if req.method == "POST"]
        self.assertEqual(len(post_requests), 1)
        self.assertEqual(
            post_requests[0].url,
            f"{ZAKEN_ROOT}statussen",
        )
