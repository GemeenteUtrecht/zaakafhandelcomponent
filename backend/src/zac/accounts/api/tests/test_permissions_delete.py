from django.contrib.sites.models import Site
from django.core import mail
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase, APITransactionTestCase
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes

from zac.core.permissions import zaakproces_send_message, zaken_handle_access
from zac.core.tests.utils import ClearCachesMixin
from zac.tests import ServiceFactory
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import mock_resource_get, paginated_response

from ...models import AtomicPermission, UserAtomicPermission
from ...tests.factories import (
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


@requests_mock.Mocker()
class DeleteAccessPermissionTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        ServiceFactory.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        ServiceFactory.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=CATALOGUS_URL,
            domein="DOME",
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            identificatie="ZT1",
            catalogus=CATALOGUS_URL,
            omschrijving="ZT1",
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
            bronorganisatie=BRONORGANISATIE,
            identificatie=IDENTIFICATIE,
            zaaktype=cls.zaaktype["url"],
        )
        cls.handler, cls.user = UserFactory.create_batch(2)
        atomic_permission = AtomicPermissionFactory.create(
            permission=zaakproces_send_message.name, object_url=ZAAK_URL
        )
        user_atomic_permission = UserAtomicPermissionFactory.create(
            user=cls.user,
            atomic_permission=atomic_permission,
        )
        cls.endpoint = reverse("accesses-detail", args=[user_atomic_permission.id])

    def setUp(self) -> None:
        super().setUp()
        self.client.force_authenticate(self.handler)

    def test_no_permissions(self, m):
        # mock ZTC and ZRC data
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)
        response = self.client.delete(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission_not_behandelaar(self, m):
        # mock ZTC and ZRC data
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
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

        response = self.client.delete(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

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
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)
        m.get(f"{ZAKEN_ROOT}rollen?zaak={ZAAK_URL}", json=paginated_response([rol]))

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_handle_access.name],
            for_user=self.handler,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        response = self.client.delete(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

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
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)
        m.get(f"{ZAKEN_ROOT}rollen?zaak={ZAAK_URL}", json=paginated_response([rol]))

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_handle_access.name, zaakproces_send_message.name],
            for_user=self.handler,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        response = self.client.delete(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_zaak_has_different_permission_and_behandelaar(self, m):
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
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
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

        response = self.client.delete(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class DeleteAccessAPITests(APITransactionTestCase):
    zaak = generate_oas_component(
        "zrc",
        "schemas/Zaak",
        url=ZAAK_URL,
        bronorganisatie=BRONORGANISATIE,
        identificatie=IDENTIFICATIE,
        zaaktype=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
    )

    def setUp(self) -> None:
        super().setUp()

        self.handler = SuperUserFactory.create()
        self.user = UserFactory.create()
        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()

        ServiceFactory.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        self.client.force_authenticate(self.handler)

    @requests_mock.Mocker()
    def test_delete_access_success(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)
        atomic_permission = AtomicPermissionFactory.create(
            object_url=self.zaak["url"], permission=zaakproces_send_message.name
        )
        user_atomic_permission = UserAtomicPermissionFactory.create(
            user=self.user, atomic_permission=atomic_permission
        )
        endpoint = reverse("accesses-detail", args=[user_atomic_permission.id])

        response = self.client.delete(endpoint)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(UserAtomicPermission.objects.count(), 0)
        self.assertEqual(AtomicPermission.objects.count(), 0)

        # test email
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        subject = _("Access Request to %(zaak)s") % {"zaak": IDENTIFICATIE}
        self.assertEqual(email.subject, subject)
        self.assertEqual(email.to, [self.user.email])
