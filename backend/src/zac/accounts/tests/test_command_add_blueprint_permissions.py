from django.core.management import call_command
from django.test import TransactionTestCase

import requests_mock
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.core.tests.utils import ClearCachesMixin
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import mock_resource_get, paginated_response

from ..models import BlueprintPermission
from .factories import RoleFactory, UserFactory

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
CATALOGUS_URL = f"{CATALOGI_ROOT}catalogi/dfb14eb7-9731-4d22-95c2-dff4f33ef36d"


@requests_mock.Mocker()
class AddBlueprintPermissionCommandTests(ClearCachesMixin, TransactionTestCase):
    def setUp(self):
        super().setUp()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        self.role = RoleFactory.create()
        self.user = UserFactory.create(username="test_user")

    def test_add_blueprint_permissions_for_zaaktype(self, m):
        # mock API requests
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        catalogus = generate_oas_component(
            "ztc", "schemas/Catalogus", url=CATALOGUS_URL, domein="some-domein"
        )
        mock_resource_get(m, catalogus)
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
            catalogus=catalogus["url"],
            omschrijving="ZT1",
        )

        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json=paginated_response([zaaktype]),
        )
        iotype = generate_oas_component(
            "ztc",
            "schemas/InformatieObjectType",
            url=f"{CATALOGI_ROOT}informatieobjecttypen/2f4c1d80-764c-45f9-95c9-32816b26a436",
            omschrijving="IOT2",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )
        mock_resource_get(m, iotype)
        ziot = generate_oas_component(
            "ztc",
            "schemas/ZaakTypeInformatieObjectType",
            zaaktype=zaaktype["url"],
            informatieobjecttype=iotype["url"],
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktype-informatieobjecttypen?zaaktype={zaaktype['url']}",
            json=paginated_response([ziot]),
        )

        call_command("add_blueprint_permissions_for_zaaktypen")

        self.assertEqual(BlueprintPermission.objects.count(), 16)
        zaak_permissions = BlueprintPermission.objects.filter(object_type="zaak")
        self.assertEqual(zaak_permissions.count(), 8)
        self.assertEqual(zaak_permissions[0].role, self.role)
        self.assertEqual(
            zaak_permissions[0].policy,
            {
                "catalogus": catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )
        doc_permissions = BlueprintPermission.objects.filter(object_type="document")
        self.assertEqual(zaak_permissions.count(), 8)
        self.assertEqual(doc_permissions[0].role, self.role)
        self.assertEqual(
            doc_permissions[0].policy,
            {
                "catalogus": catalogus["domein"],
                "iotype_omschrijving": "IOT2",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )
