from datetime import date

from django.contrib.sites.models import Site
from django.core import mail
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

import requests_mock
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase, APITransactionTestCase
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.core.permissions import (
    zaken_geforceerd_bijwerken,
    zaken_handle_access,
    zaken_inzien,
)
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import mock_resource_get, paginated_response

from ...constants import (
    AccessRequestResult,
    PermissionObjectTypeChoices,
    PermissionReason,
)
from ...models import AtomicPermission
from ...tests.factories import (
    AccessRequestFactory,
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
CATALOGUS_URL = f"{CATALOGI_ROOT}catalogi/dfb14eb7-9731-4d22-95c2-dff4f33ef36d"
ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"
ZAAK_URL = f"{ZAKEN_ROOT}zaken/482de5b2-4779-4b29-b84f-add888352182"
BRONORGANISATIE = "123456782"
IDENTIFICATIE = "ZAAK-001"


class HandleAccessRequestPermissionsTests(ClearCachesMixin, APITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.handler, self.requester = UserFactory.create_batch(2)
        self.client.force_authenticate(self.handler)

        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        self.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=CATALOGUS_URL,
            domein="DOME",
        )
        self.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            identificatie="ZT1",
            catalogus=CATALOGUS_URL,
            omschrijving="ZT1",
        )
        self.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
            bronorganisatie=BRONORGANISATIE,
            identificatie=IDENTIFICATIE,
            zaaktype=self.zaaktype["url"],
        )

        access_request = AccessRequestFactory.create(
            requester=self.requester, zaak=ZAAK_URL
        )

        self.endpoint = reverse("accessrequest-detail", args=[access_request.id])
        self.data = {
            "result": AccessRequestResult.approve,
            "permissions": [zaken_handle_access.name],
        }

    def test_no_permissions(self):
        response = self.client.patch(self.endpoint, self.data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_permission_not_behandelaar(self, m):
        # mock ZTC and ZRC data
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaak)
        m.get(f"{ZAKEN_ROOT}rollen?zaak={ZAAK_URL}", json=paginated_response([]))

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_handle_access.name],
            for_user=self.handler,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        response = self.client.patch(self.endpoint, self.data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_zaak_has_permission_and_behandelaar(self, m):
        # mock ZTC and ZRC data
        rol = {
            "url": f"{ZAKEN_ROOT}rollen/b80022cf-6084-4cf6-932b-799effdcdb26",
            "zaak": self.zaak["url"],
            "betrokkene": None,
            "betrokkeneType": "medewerker",
            "roltype": f"{CATALOGI_ROOT}roltypen/bfd62804-f46c-42e7-a31c-4139b4c661ac",
            "omschrijving": "zaak behandelaar",
            "omschrijvingGeneriek": "behandelaar",
            "roltoelichting": "some description",
            "registratiedatum": "2020-09-01T00:00:00Z",
            "indicatieMachtiging": "",
            "betrokkeneIdentificatie": {
                "identificatie": self.handler.username,
            },
        }
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaak)
        m.get(f"{ZAKEN_ROOT}rollen?zaak={ZAAK_URL}", json=paginated_response([rol]))

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_handle_access.name],
            for_user=self.handler,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        response = self.client.patch(self.endpoint, self.data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @requests_mock.Mocker()
    def test_zaak_has_permission_and_behandelaar_but_zaak_is_closed(self, m):
        # mock ZTC and ZRC data
        rol = {
            "url": f"{ZAKEN_ROOT}rollen/b80022cf-6084-4cf6-932b-799effdcdb26",
            "zaak": self.zaak["url"],
            "betrokkene": None,
            "betrokkeneType": "medewerker",
            "roltype": f"{CATALOGI_ROOT}roltypen/bfd62804-f46c-42e7-a31c-4139b4c661ac",
            "omschrijving": "zaak behandelaar",
            "omschrijvingGeneriek": "behandelaar",
            "roltoelichting": "some description",
            "registratiedatum": "2020-09-01T00:00:00Z",
            "indicatieMachtiging": "",
            "betrokkeneIdentificatie": {
                "identificatie": self.handler.username,
            },
        }
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.catalogus)
        m.get(ZAAK_URL, json={**self.zaak, "einddatum": "2020-01-01"})
        m.get(f"{ZAKEN_ROOT}rollen?zaak={ZAAK_URL}", json=paginated_response([rol]))

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_handle_access.name],
            for_user=self.handler,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        response = self.client.patch(self.endpoint, self.data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_zaak_has_permission_and_behandelaar_for_closed_zaak(self, m):
        # mock ZTC and ZRC data
        rol = {
            "url": f"{ZAKEN_ROOT}rollen/b80022cf-6084-4cf6-932b-799effdcdb26",
            "zaak": self.zaak["url"],
            "betrokkene": None,
            "betrokkeneType": "medewerker",
            "roltype": f"{CATALOGI_ROOT}roltypen/bfd62804-f46c-42e7-a31c-4139b4c661ac",
            "omschrijving": "zaak behandelaar",
            "omschrijvingGeneriek": "behandelaar",
            "roltoelichting": "some description",
            "registratiedatum": "2020-09-01T00:00:00Z",
            "indicatieMachtiging": "",
            "betrokkeneIdentificatie": {
                "identificatie": self.handler.username,
            },
        }
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.catalogus)
        m.get(ZAAK_URL, json={**self.zaak, "einddatum": "2020-01-01"})
        m.get(f"{ZAKEN_ROOT}rollen?zaak={ZAAK_URL}", json=paginated_response([rol]))

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_geforceerd_bijwerken.name],
            for_user=self.handler,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_handle_access.name],
            for_user=self.handler,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        response = self.client.patch(self.endpoint, self.data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)


@freeze_time("2020-01-01")
class HandleAccessRequestAPITests(APITransactionTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.handler = SuperUserFactory.create()
        self.requester = UserFactory.create()

        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()

        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        self.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
            bronorganisatie=BRONORGANISATIE,
            identificatie=IDENTIFICATIE,
            zaaktype=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
        )

        self.client.force_authenticate(self.handler)

    @requests_mock.Mocker()
    def test_handle_request_access_approve(self, m):
        # mock ZRC data
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)

        access_request = AccessRequestFactory.create(
            requester=self.requester, zaak=ZAAK_URL
        )
        endpoint = reverse("accessrequest-detail", args=[access_request.id])

        data = {
            "result": AccessRequestResult.approve,
            "handler_comment": "some comment",
            "start_date": "2020-01-02",
            "end_date": "2021-01-01",
            "permissions": [zaken_inzien.name, zaken_handle_access.name],
        }

        response = self.client.patch(endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(AtomicPermission.objects.for_user(self.requester).count(), 2)
        self.assertTrue(
            AtomicPermission.objects.for_user(self.requester)
            .filter(permission=zaken_inzien.name)
            .exists()
        )
        self.assertTrue(
            AtomicPermission.objects.for_user(self.requester)
            .filter(permission=zaken_handle_access.name)
            .exists()
        )

        access_request.refresh_from_db()

        self.assertEqual(access_request.handler, self.handler)
        self.assertEqual(access_request.result, AccessRequestResult.approve)
        self.assertEqual(access_request.handled_date, date(2020, 1, 1))

        for perm in [zaken_inzien.name, zaken_handle_access.name]:
            uap = access_request.useratomicpermission_set.get(
                atomic_permission__permission=perm
            )
            self.assertEqual(uap.comment, "some comment")
            self.assertEqual(uap.user, self.requester)
            self.assertEqual(uap.reason, PermissionReason.toegang_verlenen)
            self.assertEqual(uap.start_date.date(), date(2020, 1, 2))
            self.assertEqual(uap.end_date.date(), date(2021, 1, 1))
            atomic_permission = uap.atomic_permission
            self.assertEqual(atomic_permission.object_url, ZAAK_URL)
            self.assertEqual(
                atomic_permission.object_type, PermissionObjectTypeChoices.zaak
            )

        data = response.json()

        self.assertEqual(
            data,
            {
                "url": f"http://testserver{endpoint}",
                "requester": self.requester.username,
                "handler": self.handler.username,
                "result": AccessRequestResult.approve,
                "handlerComment": "some comment",
                "startDate": "2020-01-02",
                "endDate": "2021-01-01",
                "permissions": ["zaken:inzien", "zaken:toegang-verlenen"],
            },
        )

        # test email
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        subject = _("Access Request to %(zaak)s") % {"zaak": IDENTIFICATIE}
        self.assertEqual(email.subject, subject)
        self.assertEqual(email.to, [self.requester.email])

        zaak_detail_path = f"/ui/zaken/{BRONORGANISATIE}/{IDENTIFICATIE}"
        url = f"http://testserver{zaak_detail_path}"
        self.assertIn(url, email.body)

    @requests_mock.Mocker()
    def test_handle_access_request_reject(self, m):
        # mock ZRC data
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)

        access_request = AccessRequestFactory.create(
            requester=self.requester, zaak=ZAAK_URL
        )
        endpoint = reverse("accessrequest-detail", args=[access_request.id])

        data = {
            "result": AccessRequestResult.reject,
            "handler_comment": "some comment",
            "start_date": "2020-01-02",
            "end_date": "2021-01-01",
            "permissions": [zaken_inzien.name],
        }

        response = self.client.patch(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(AtomicPermission.objects.for_user(self.requester).count(), 0)

        access_request.refresh_from_db()

        self.assertEqual(access_request.handler, self.handler)
        self.assertEqual(access_request.result, AccessRequestResult.reject)
        self.assertEqual(access_request.handled_date, date(2020, 1, 1))
        self.assertEqual(access_request.useratomicpermission_set.count(), 0)

        data = response.json()

        self.assertEqual(
            data,
            {
                "url": f"http://testserver{endpoint}",
                "requester": self.requester.username,
                "handler": self.handler.username,
                "result": AccessRequestResult.reject,
                "handlerComment": "some comment",
                "startDate": "2020-01-02",
                "endDate": "2021-01-01",
                "permissions": [zaken_inzien.name],
            },
        )

        # test email
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        subject = _("Access Request to %(zaak)s") % {"zaak": IDENTIFICATIE}
        self.assertEqual(email.subject, subject)
        self.assertEqual(email.to, [self.requester.email])

        zaak_detail_path = f"/ui/zaken/{BRONORGANISATIE}/{IDENTIFICATIE}"
        url = f"http://testserver{zaak_detail_path}"
        self.assertNotIn(url, email.body)

    @requests_mock.Mocker()
    def test_handle_access_request_with_result(self, m):
        # mock ZRC data
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)

        access_request = AccessRequestFactory.create(
            requester=self.requester, zaak=ZAAK_URL, result=AccessRequestResult.reject
        )
        endpoint = reverse("accessrequest-detail", args=[access_request.id])

        data = {
            "result": AccessRequestResult.approve,
            "handler_comment": "some comment",
            "start_date": "2020-01-02",
            "end_date": "2021-01-01",
            "permissions": [zaken_inzien.name],
        }

        response = self.client.patch(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "nonFieldErrors",
                    "code": "invalid",
                    "reason": "Dit toegangsverzoek is al afgehandeld.",
                }
            ],
        )

    @requests_mock.Mocker()
    def test_handle_access_request_empty_result(self, m):
        # mock ZRC data
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)

        access_request = AccessRequestFactory.create(
            requester=self.requester, zaak=ZAAK_URL
        )
        endpoint = reverse("accessrequest-detail", args=[access_request.id])

        data = {
            "handler_comment": "some comment",
            "start_date": "2020-01-02",
            "end_date": "2021-01-01",
            "permissions": [zaken_inzien.name],
        }

        response = self.client.patch(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "nonFieldErrors",
                    "code": "invalid",
                    "reason": "'result'-veld moet gedefinieerd zijn wanneer een toegangsverzoek in behandeling wordt genomen.",
                }
            ],
        )

    @requests_mock.Mocker()
    def test_handle_access_request_empty_permissions(self, m):
        # mock ZRC data
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)

        access_request = AccessRequestFactory.create(
            requester=self.requester, zaak=ZAAK_URL
        )
        endpoint = reverse("accessrequest-detail", args=[access_request.id])

        data = {
            "result": AccessRequestResult.approve,
            "handler_comment": "some comment",
            "start_date": "2020-01-02",
            "end_date": "2021-01-01",
        }

        response = self.client.patch(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "nonFieldErrors",
                    "code": "invalid",
                    "reason": "'permissions'-veld moet gedefinieerd zijn wanneer een toegangsverzoek in behandeling wordt genomen.",
                }
            ],
        )
