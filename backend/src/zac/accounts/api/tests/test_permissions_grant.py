from datetime import date, datetime

from django.contrib.sites.models import Site
from django.core import mail
from django.urls import reverse
from django.utils import timezone
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
from zac.tests.utils import paginated_response

from ...constants import (
    AccessRequestResult,
    PermissionObjectTypeChoices,
    PermissionReason,
)
from ...models import AtomicPermission, UserAtomicPermission
from ...tests.factories import (
    AccessRequestFactory,
    AtomicPermissionFactory,
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserAtomicPermissionFactory,
    UserFactory,
)

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
CATALOGUS_URL = f"{CATALOGI_ROOT}catalogi/dfb14eb7-9731-4d22-95c2-dff4f33ef36d"
ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"
ZAAK_URL = f"{ZAKEN_ROOT}zaken/482de5b2-4779-4b29-b84f-add888352182"
BRONORGANISATIE = "123456782"
IDENTIFICATIE = "ZAAK-001"


class GrantAccessPermissionTests(ClearCachesMixin, APITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.handler, self.requester = UserFactory.create_batch(2)
        self.client.force_authenticate(self.handler)

        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
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

        self.endpoint = reverse("accesses-list")
        self.data = [
            {
                "requester": self.requester.username,
                "zaak": ZAAK_URL,
                "comment": "some comment",
                "permission": zaken_handle_access.name,
            }
        ]

    def test_no_permissions(self):
        response = self.client.post(self.endpoint, self.data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_permission_not_behandelaar(self, m):
        # mock ZTC and ZRC data
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(ZAAK_URL, json=self.zaak)
        m.get(f"{ZAKEN_ROOT}rollen?zaak={ZAAK_URL}", json=paginated_response([]))

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_handle_access.name],
            for_user=self.handler,
            policy={
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        response = self.client.post(self.endpoint, self.data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_permission_but_for_other_zaaktype(self, m):
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
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(ZAAK_URL, json=self.zaak)
        m.get(f"{ZAKEN_ROOT}rollen?zaak={ZAAK_URL}", json=paginated_response([rol]))

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_handle_access.name],
            for_user=self.handler,
            policy={
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        response = self.client.post(self.endpoint, self.data)

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
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(ZAAK_URL, json=self.zaak)
        m.get(f"{ZAKEN_ROOT}rollen?zaak={ZAAK_URL}", json=paginated_response([rol]))

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_handle_access.name],
            for_user=self.handler,
            policy={
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        response = self.client.post(self.endpoint, self.data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

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
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(ZAAK_URL, json={**self.zaak, "einddatum": "2020-01-01"})
        m.get(f"{ZAKEN_ROOT}rollen?zaak={ZAAK_URL}", json=paginated_response([rol]))

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_handle_access.name],
            for_user=self.handler,
            policy={
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        response = self.client.post(self.endpoint, self.data)

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
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(ZAAK_URL, json={**self.zaak, "einddatum": "2020-01-01"})
        m.get(f"{ZAKEN_ROOT}rollen?zaak={ZAAK_URL}", json=paginated_response([rol]))

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_geforceerd_bijwerken.name],
            for_user=self.handler,
            policy={
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_handle_access.name],
            for_user=self.handler,
            policy={
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        response = self.client.post(self.endpoint, self.data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


@freeze_time("2020-01-01")
class GrantAccessAPITests(APITransactionTestCase):
    """
    Test GrantZaakAccessView
    """

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
        self.endpoint = reverse("accesses-list")

    @requests_mock.Mocker()
    def test_grant_access_success(self, m):
        # mock ZRC data
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(ZAAK_URL, json=self.zaak)

        data = [
            {
                "requester": self.requester.username,
                "zaak": ZAAK_URL,
                "comment": "some comment",
                "permission": "zaken:inzien",
            },
            {
                "requester": self.requester.username,
                "zaak": ZAAK_URL,
                "comment": "some comment",
                "permission": "zaken:toegang-verlenen",
            },
        ]

        response = self.client.post(self.endpoint, data)
        results = response.json()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
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

        for perm in ["zaken:inzien", "zaken:toegang-verlenen"]:
            atomic_permission = AtomicPermission.objects.for_user(self.requester).get(
                permission=perm
            )

            self.assertEqual(atomic_permission.object_url, ZAAK_URL)
            self.assertEqual(
                atomic_permission.object_type, PermissionObjectTypeChoices.zaak
            )
            self.assertEqual(atomic_permission.permission, perm)

            user_atomic_permission = atomic_permission.useratomicpermission_set.get()
            self.assertEqual(
                user_atomic_permission.reason, PermissionReason.toegang_verlenen
            )
            self.assertEqual(user_atomic_permission.start_date.date(), date(2020, 1, 1))
            self.assertIsNone(user_atomic_permission.end_date)
            self.assertTrue(
                {
                    "id": user_atomic_permission.id,
                    "permission": perm,
                    "requester": self.requester.username,
                    "zaak": ZAAK_URL,
                    "startDate": "2020-01-01T00:00:00Z",
                    "endDate": None,
                    "reason": PermissionReason.toegang_verlenen,
                    "comment": "some comment",
                }
                in results
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
    def test_grant_access_no_user(self, m):
        data = [
            {
                "requester": "some user",
                "zaak": ZAAK_URL,
                "comment": "some comment",
                "permission": "zaken:inzien",
            }
        ]

        response = self.client.post(self.endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue("requester" in response.json()[0])

    def test_grant_access_with_existing_permission(self):
        AtomicPermissionFactory.create(
            object_url=ZAAK_URL,
            object_type=PermissionObjectTypeChoices.zaak,
            permission=zaken_inzien.name,
            for_user=self.requester,
        )
        data = [
            {
                "requester": self.requester.username,
                "zaak": ZAAK_URL,
                "comment": "some comment",
                "permission": "zaken:inzien",
            }
        ]

        response = self.client.post(self.endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()[0]["nonFieldErrors"],
            [
                "`{user}` heeft al het recht `zaken:inzien`.".format(
                    user=self.requester.username
                )
            ],
        )

    @requests_mock.Mocker()
    def test_grant_access_with_existing_permission_expired(self, m):
        # mock ZRC data
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(ZAAK_URL, json=self.zaak)

        UserAtomicPermissionFactory.create(
            atomic_permission__object_url=ZAAK_URL,
            atomic_permission__object_type=PermissionObjectTypeChoices.zaak,
            atomic_permission__permission=zaken_inzien.name,
            user=self.requester,
            end_date=timezone.make_aware(datetime(2019, 12, 31)),
        )
        data = [
            {
                "requester": self.requester.username,
                "zaak": ZAAK_URL,
                "comment": "some comment",
                "permission": "zaken:inzien",
            }
        ]
        response = self.client.post(self.endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            UserAtomicPermission.objects.filter(user=self.requester).actual().count(), 1
        )

        user_atomic_permission = (
            UserAtomicPermission.objects.filter(user=self.requester).actual().get()
        )
        atomic_permission = user_atomic_permission.atomic_permission

        self.assertEqual(atomic_permission.object_url, ZAAK_URL)
        self.assertEqual(
            atomic_permission.object_type, PermissionObjectTypeChoices.zaak
        )
        self.assertEqual(atomic_permission.permission, zaken_inzien.name)

        self.assertIsNone(user_atomic_permission.end_date)

        # check email
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, [self.requester.email])

        zaak_detail_path = f"/ui/zaken/{BRONORGANISATIE}/{IDENTIFICATIE}"
        url = f"http://testserver{zaak_detail_path}"
        self.assertIn(url, email.body)

    @requests_mock.Mocker()
    def test_grant_access_with_existing_pending_request(self, m):
        # mock ZRC data
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(ZAAK_URL, json=self.zaak)

        pending_request = AccessRequestFactory.create(
            requester=self.requester, result="", zaak=ZAAK_URL
        )
        data = [
            {
                "requester": self.requester.username,
                "zaak": ZAAK_URL,
                "comment": "some comment",
                "permission": "zaken:inzien",
                "end_date": "2021-01-01T00:00:00Z",
            }
        ]

        response = self.client.post(self.endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user_atomic_permission = UserAtomicPermission.objects.filter(
            user=self.requester
        ).get()
        atomic_permission = user_atomic_permission.atomic_permission

        pending_request.refresh_from_db()
        self.assertEqual(pending_request.result, AccessRequestResult.approve)
        self.assertEqual(
            pending_request.useratomicpermission_set.all()[0], user_atomic_permission
        )

        self.assertEqual(atomic_permission.object_url, ZAAK_URL)
        self.assertEqual(
            atomic_permission.object_type, PermissionObjectTypeChoices.zaak
        )
        self.assertEqual(atomic_permission.permission, zaken_inzien.name)

        self.assertEqual(user_atomic_permission.end_date.date(), date(2021, 1, 1))

        # check email
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, [self.requester.email])

        zaak_detail_path = f"/ui/zaken/{BRONORGANISATIE}/{IDENTIFICATIE}"
        url = f"http://testserver{zaak_detail_path}"
        self.assertIn(url, email.body)
