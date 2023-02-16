from django.urls import reverse_lazy

import requests_mock
from rest_framework.test import APITransactionTestCase
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.datastructures import VA_ORDER
from zac.accounts.tests.factories import (
    AtomicPermissionFactory,
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.camunda.constants import AssigneeTypeChoices
from zac.core.permissions import zaken_inzien
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.documents import ZaakDocument, ZaakTypeDocument
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.utils import paginated_response

from ..api.permissions import management_dashboard_inzien

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"


class ManagementDashboardSummaryTests(
    ClearCachesMixin, ESMixin, APITransactionTestCase
):
    endpoint = reverse_lazy("management-dashboard-summary")

    def setUp(self) -> None:
        super().setUp()
        self.zaaktype_document1 = ZaakTypeDocument(
            url=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
            catalogus=f"{CATALOGI_ROOT}catalogussen/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            omschrijving="zaaktype1",
            identificatie="zaaktype_id_1",
        )
        self.zaak_document1 = ZaakDocument(
            meta={"id": "a522d30c-6c10-47fe-82e3-e9f524c14ca8"},
            url=f"{ZAKEN_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            zaaktype=self.zaaktype_document1,
            identificatie="ZAAK-2022-0000001010",
            bronorganisatie="123456",
            omschrijving="Some zaak description",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            va_order=VA_ORDER[VertrouwelijkheidsAanduidingen.openbaar],
            rollen=[
                {
                    "url": f"{ZAKEN_ROOT}rollen/b80022cf-6084-4cf6-932b-799effdcdb26",
                    "betrokkene_type": "organisatorische_eenheid",
                    "betrokkene_identificatie": {
                        "identificatie": "123456",
                    },
                },
                {
                    "url": f"{ZAKEN_ROOT}rollen/de7039d7-242a-4186-91c3-c3b49228211a",
                    "betrokkene_type": "medewerker",
                    "omschrijving_generiek": "behandelaar",
                    "betrokkene_identificatie": {
                        "identificatie": f"{AssigneeTypeChoices.user}:some_username",
                    },
                },
            ],
            eigenschappen={
                "tekst": {
                    "Beleidsveld": "Asiel en Integratie",
                    "Bedrag incl  BTW": "aaa",
                }
            },
            deadline="2021-12-31",
        )
        self.zaak_document1.save()
        self.zaaktype_document2 = ZaakTypeDocument(
            url=f"{CATALOGI_ROOT}zaaktypen/de7039d7-242a-4186-91c3-c3b49228211a",
            catalogus=f"{CATALOGI_ROOT}catalogussen/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            omschrijving="zaaktype2",
            identificatie="zaaktype_id_2",
        )
        self.zaak_document2 = ZaakDocument(
            meta={"id": "a8c8bc90-defa-4548-bacd-793874c013ab"},
            url="https://api.zaken.nl/api/v1/zaken/a8c8bc90-defa-4548-bacd-793874c013ab",
            zaaktype=self.zaaktype_document2,
            identificatie="ZAAK-2021-000000105",
            bronorganisatie="7890",
            omschrijving="een omschrijving",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            va_order=VA_ORDER[VertrouwelijkheidsAanduidingen.zaakvertrouwelijk],
            rollen=[],
            eigenschappen={"tekst": {"Beleidsveld": "Integratie"}},
            deadline="2021-12-31",
        )
        self.zaak_document2.save()
        self.refresh_index()

    def test_management_dashboard_summary_not_authenticated(self):
        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, 403)

    def test_management_dashboard_summary_authenticated_no_permissions(self):
        user = UserFactory.create()
        self.client.force_authenticate(user)
        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, 403)

    def test_management_dashboard_summary_superuser(self):
        user = SuperUserFactory.create()
        self.client.force_authenticate(user)
        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, 200)

    def test_count_by_zaaktype_blueprint_permissions(self):
        user = UserFactory.create()
        self.client.force_authenticate(user)

        BlueprintPermissionFactory.create(
            role__permissions=[management_dashboard_inzien.name],
            policy={
                "catalogus": self.zaaktype_document1.catalogus,
                "zaaktype_omschrijving": self.zaaktype_document1.omschrijving,
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
            for_user=user,
        )

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            policy={
                "catalogus": self.zaaktype_document1.catalogus,
                "zaaktype_omschrijving": self.zaaktype_document1.omschrijving,
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
            for_user=user,
        )

        response = self.client.post(self.endpoint)
        self.assertEqual(len(response.json()), 1)

    def test_count_by_zaaktype_atomic_permissions(self):
        user = UserFactory.create()
        self.client.force_authenticate(user)

        AtomicPermissionFactory.create(
            permission=zaken_inzien.name,
            object_url=self.zaak_document1.url,
            for_user=user,
        )

        AtomicPermissionFactory.create(
            permission=management_dashboard_inzien.name,
            object_url=self.zaak_document1.url,
            for_user=user,
        )

        response = self.client.post(self.endpoint)
        self.assertEqual(len(response.json()), 1)

    @requests_mock.Mocker()
    def test_management_dashboard_summary_superuser_response(self, m):
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        zt = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=self.zaaktype_document1.url,
            identificatie=self.zaaktype_document1.identificatie,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving=self.zaaktype_document1.omschrijving,
            catalogus=self.zaaktype_document1.catalogus,
        )
        zt2 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=self.zaaktype_document2.url,
            identificatie=self.zaaktype_document2.identificatie,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving=self.zaaktype_document2.omschrijving,
            catalogus=self.zaaktype_document2.catalogus,
        )
        m.get(f"{CATALOGI_ROOT}zaaktypen", json=paginated_response([zt, zt2]))
        user = SuperUserFactory.create()
        self.client.force_authenticate(user)
        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [
                {
                    "catalogus": "https://api.catalogi.nl/api/v1/catalogussen/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
                    "zaaktypen": [
                        {
                            "zaaktypeOmschrijving": "zaaktype1",
                            "zaaktypeCatalogus": "https://api.catalogi.nl/api/v1/catalogussen/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
                            "count": 1,
                            "zaaktypeIdentificatie": "zaaktype_id_1",
                        },
                        {
                            "zaaktypeOmschrijving": "zaaktype2",
                            "zaaktypeCatalogus": "https://api.catalogi.nl/api/v1/catalogussen/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
                            "count": 1,
                            "zaaktypeIdentificatie": "zaaktype_id_2",
                        },
                    ],
                    "count": 2,
                }
            ],
        )
