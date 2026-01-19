from copy import deepcopy
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

import requests_mock
from zgw_consumers.constants import APITypes

from zac.contrib.objects.kownsl.tests.factories import review_request_factory
from zac.contrib.objects.services import factory_review_request
from zac.core.permissions import zaakproces_usertasks, zaken_inzien
from zac.core.tests.utils import ClearCachesMixin
from zac.tests import ServiceFactory
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import paginated_response

from ..constants import PermissionObjectTypeChoices
from ..models import AtomicPermission
from .factories import UserFactory

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"


@requests_mock.Mocker()
class AddPermissionCommandTests(ClearCachesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ServiceFactory.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        ServiceFactory.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

        cls.user = UserFactory.create(username="test_user")

    def test_add_permission_for_behandelaar(self, m):
        # mock API requests
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

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
        with patch(
            "zac.accounts.management.commands.add_atomic_permissions.get_all_review_requests_for_zaak",
            return_value=[],
        ):
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
        with patch(
            "zac.accounts.management.commands.add_atomic_permissions.get_all_review_requests_for_zaak",
            return_value=[],
        ):
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
        review_request = review_request_factory(
            zaak=zaak["url"], userDeadlines={f"user:{self.user.username}": "2099-01-01"}
        )

        m.get(f"{CATALOGI_ROOT}zaaktypen", json=paginated_response([zaaktype]))
        m.get(f"{ZAKEN_ROOT}zaken", json=paginated_response([zaak]))
        m.get(f"{ZAKEN_ROOT}rollen", json=paginated_response([]))

        with patch(
            "zac.accounts.management.commands.add_atomic_permissions.get_all_review_requests_for_zaak",
            return_value=[factory_review_request(review_request)],
        ):
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
