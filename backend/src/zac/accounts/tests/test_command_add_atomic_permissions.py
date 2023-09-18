from django.core.management import call_command
from django.test import TestCase

import requests_mock
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.contrib.kownsl.models import KownslConfig
from zac.core.permissions import zaakproces_usertasks, zaken_inzien
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import paginated_response

from ..constants import PermissionObjectTypeChoices
from ..models import AtomicPermission
from .factories import UserFactory

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"
KOWNSL_ROOT = "https://kownsl.nl/"


@requests_mock.Mocker()
class AddPermissionCommandTests(ClearCachesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        kownsl = Service.objects.create(api_type=APITypes.orc, api_root=KOWNSL_ROOT)

        config = KownslConfig.get_solo()
        config.service = kownsl
        config.save()

        cls.user = UserFactory.create(username="test_user")
        cls.token = Token.objects.get_or_create(user=cls.user)

    def test_add_permission_for_behandelaar(self, m):
        # mock API requests
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
        )
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/69e98129-1f0d-497f-bbfb-84b88137edbc",
            zaaktype=zaaktype["url"],
            bronorganisatie="002220647",
            identificatie="ZAAK1",
            vertrouwelijkheidaanduiding="zaakvertrouwelijk",
            eigenschappen=[],
        )
        rol = {
            "url": f"{ZAKEN_ROOT}rollen/b80022cf-6084-4cf6-932b-799effdcdb26",
            "zaak": zaak["url"],
            "betrokkene": None,
            "betrokkeneType": "medewerker",
            "roltype": f"{CATALOGI_ROOT}roltypen/bfd62804-f46c-42e7-a31c-4139b4c661ac",
            "omschrijving": "zaak behandelaar",
            "omschrijvingGeneriek": "behandelaar",
            "roltoelichting": "some description",
            "registratiedatum": "2020-09-01T00:00:00Z",
            "indicatieMachtiging": "",
            "betrokkeneIdentificatie": {
                "identificatie": self.user.username,
            },
        }
        m.get(f"{CATALOGI_ROOT}zaaktypen", json=paginated_response([zaaktype]))
        m.get(f"{ZAKEN_ROOT}zaken", json=paginated_response([zaak]))
        m.get(f"{ZAKEN_ROOT}rollen", json=paginated_response([rol]))
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests?for_zaak={zaak['url']}",
            json=paginated_response([]),
        )

        call_command("add_atomic_permissions")

        self.assertEqual(AtomicPermission.objects.for_user(self.user).count(), 1)

        atomic_permission = AtomicPermission.objects.for_user(self.user).get()

        self.assertEqual(atomic_permission.permission, zaken_inzien.name)
        self.assertEqual(
            atomic_permission.object_type, PermissionObjectTypeChoices.zaak
        )
        self.assertEqual(atomic_permission.object_url, zaak["url"])

    def test_add_permission_for_initiator(self, m):
        # mock API requests
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
        )
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/69e98129-1f0d-497f-bbfb-84b88137edbc",
            zaaktype=zaaktype["url"],
            bronorganisatie="002220647",
            identificatie="ZAAK1",
            vertrouwelijkheidaanduiding="zaakvertrouwelijk",
            eigenschappen=[],
        )
        rol = {
            "url": f"{ZAKEN_ROOT}rollen/b80022cf-6084-4cf6-932b-799effdcdb26",
            "zaak": zaak["url"],
            "betrokkene": None,
            "betrokkeneType": "medewerker",
            "roltype": f"{CATALOGI_ROOT}roltypen/bfd62804-f46c-42e7-a31c-4139b4c661ac",
            "omschrijving": "hoofdbehandelaar",
            "omschrijvingGeneriek": "initiator",
            "roltoelichting": "some description",
            "registratiedatum": "2020-09-01T00:00:00Z",
            "indicatieMachtiging": "",
            "betrokkeneIdentificatie": {
                "identificatie": self.user.username,
            },
        }
        m.get(f"{CATALOGI_ROOT}zaaktypen", json=paginated_response([zaaktype]))
        m.get(f"{ZAKEN_ROOT}zaken", json=paginated_response([zaak]))
        m.get(f"{ZAKEN_ROOT}rollen", json=paginated_response([rol]))
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests?for_zaak={zaak['url']}",
            json=paginated_response([]),
        )

        call_command("add_atomic_permissions")

        self.assertEqual(AtomicPermission.objects.for_user(self.user).count(), 1)

        atomic_permission = AtomicPermission.objects.for_user(self.user).get()

        self.assertEqual(atomic_permission.permission, zaken_inzien.name)
        self.assertEqual(
            atomic_permission.object_type, PermissionObjectTypeChoices.zaak
        )
        self.assertEqual(atomic_permission.object_url, zaak["url"])

    def test_add_permission_for_advisor(self, m):
        # mock API requests
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
        )
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/69e98129-1f0d-497f-bbfb-84b88137edbc",
            zaaktype=zaaktype["url"],
            bronorganisatie="002220647",
            identificatie="ZAAK1",
            vertrouwelijkheidaanduiding="zaakvertrouwelijk",
            eigenschappen=[],
        )
        review_request = {
            "id": "1b864f55-0880-4207-9246-9b454cb69cca",
            "created": "2020-12-16T14:15:22Z",
            "forZaak": zaak["url"],
            "reviewType": "advice",
            "documents": [],
            "frontendUrl": "",
            "numAdvices": 0,
            "numApprovals": 0,
            "numAssignedUsers": 0,
            "toelichting": "",
            "userDeadlines": {f"user:{self.user.username}": "2099-01-01"},
        }
        m.get(f"{CATALOGI_ROOT}zaaktypen", json=paginated_response([zaaktype]))
        m.get(f"{ZAKEN_ROOT}zaken", json=paginated_response([zaak]))
        m.get(f"{ZAKEN_ROOT}rollen", json=paginated_response([]))
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests?for_zaak={zaak['url']}",
            json=paginated_response([review_request]),
        )

        call_command("add_atomic_permissions")

        self.assertEqual(AtomicPermission.objects.for_user(self.user).count(), 2)

        permission_read, permission_execute = AtomicPermission.objects.for_user(
            self.user
        )

        self.assertEqual(permission_read.permission, zaken_inzien.name)
        self.assertEqual(permission_execute.permission, zaakproces_usertasks.name)

        for permission in [permission_read, permission_execute]:
            self.assertEqual(permission.object_type, PermissionObjectTypeChoices.zaak)
            self.assertEqual(permission.object_url, zaak["url"])
