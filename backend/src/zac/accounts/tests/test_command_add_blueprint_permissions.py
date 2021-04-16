from django.core.management import call_command
from django.test import TestCase

import requests_mock
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import paginated_response

from ..models import BlueprintPermission
from .factories import UserFactory

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"


@requests_mock.Mocker()
class AddBlueprintPermissionCommandTests(ClearCachesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        cls.user = UserFactory.create(username="test_user")

    def test_add_blueprint_permissions_for_zaaktype(self, m):
        # mock API requests
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
            omschrijving="ZT1",
        )
        m.get(f"{CATALOGI_ROOT}zaaktypen", json=paginated_response([zaaktype]))

        call_command("add_blueprint_permissions_for_zaaktypen")

        self.assertEqual(BlueprintPermission.objects.count(), 13)
        for permission in BlueprintPermission.objects.all():
            self.assertEqual(
                permission.policy,
                {
                    "catalogus": zaaktype["catalogus"],
                    "zaktype_omschrijving": "ZT1",
                    "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
                },
            )
