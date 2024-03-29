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
from zac.tests.utils import mock_resource_get, paginated_response

from ..api.permissions import management_dashboard_inzien

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"
CATALOGUS_URL = f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"


class ManagementDashboardDetailTests(ClearCachesMixin, ESMixin, APITransactionTestCase):
    endpoint = reverse_lazy("management-dashboard")
    catalogus = generate_oas_component(
        "ztc",
        "schemas/Catalogus",
        url=CATALOGUS_URL,
        domein="DOME",
    )

    def setUp(self) -> None:
        super().setUp()
        self.zaaktype_document1 = ZaakTypeDocument(
            url=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
            catalogus_domein="DOME",
            catalogus=CATALOGUS_URL,
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
            catalogus_domein="DOME",
            catalogus=CATALOGUS_URL,
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

    def test_management_dashboard_detail_not_authenticated(self):
        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, 403)

    def test_management_dashboard_detail_authenticated_no_permissions(self):
        user = UserFactory.create()
        self.client.force_authenticate(user)
        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, 403)

    @requests_mock.Mocker()
    def test_management_dashboard_detail_superuser(self, m):
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        zt = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=self.zaaktype_document1.url,
            identificatie=self.zaaktype_document1.identificatie,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving=self.zaaktype_document1.omschrijving,
            catalogus=self.zaaktype_document1.catalogus,
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={zt['catalogus']}",
            json=paginated_response([zt]),
        )
        user = SuperUserFactory.create()
        self.client.force_authenticate(user)
        response = self.client.post(
            self.endpoint,
            data={
                "zaaktype": {
                    "omschrijving": zt["omschrijving"],
                    "catalogus": zt["catalogus"],
                }
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "fields": [
                    "bronorganisatie",
                    "deadline",
                    "identificatie",
                    "omschrijving",
                    "startdatum",
                    "status",
                    "vertrouwelijkheidaanduiding",
                    "zaaktype",
                ],
                "next": None,
                "previous": None,
                "count": 1,
                "results": [
                    {
                        "url": None,
                        "zaaktype": {
                            "url": "https://api.catalogi.nl/api/v1/zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
                            "catalogus": CATALOGUS_URL,
                            "catalogusDomein": self.catalogus["domein"],
                            "omschrijving": "zaaktype1",
                            "identificatie": "zaaktype_id_1",
                        },
                        "identificatie": "ZAAK-2022-0000001010",
                        "bronorganisatie": "123456",
                        "omschrijving": "Some zaak description",
                        "vertrouwelijkheidaanduiding": "openbaar",
                        "vaOrder": None,
                        "rollen": [],
                        "startdatum": None,
                        "einddatum": None,
                        "registratiedatum": None,
                        "deadline": "2021-12-31T00:00:00Z",
                        "eigenschappen": [],
                        "status": {
                            "url": None,
                            "statustype": None,
                            "datumStatusGezet": None,
                            "statustoelichting": None,
                        },
                        "toelichting": None,
                        "zaakgeometrie": None,
                    }
                ],
            },
        )

    @requests_mock.Mocker()
    def test_management_dashboard_detail_blueprint(self, m):
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        zt = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=self.zaaktype_document1.url,
            identificatie=self.zaaktype_document1.identificatie,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving=self.zaaktype_document1.omschrijving,
            catalogus=self.zaaktype_document1.catalogus,
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={zt['catalogus']}",
            json=paginated_response([zt]),
        )
        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[management_dashboard_inzien.name],
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": self.zaaktype_document1.omschrijving,
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
            for_user=user,
        )

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": self.zaaktype_document1.omschrijving,
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
            for_user=user,
        )

        self.client.force_authenticate(user)
        response = self.client.post(
            self.endpoint,
            data={
                "zaaktype": {
                    "omschrijving": zt["omschrijving"],
                    "catalogus": zt["catalogus"],
                }
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "fields": [
                    "bronorganisatie",
                    "deadline",
                    "identificatie",
                    "omschrijving",
                    "startdatum",
                    "status",
                    "vertrouwelijkheidaanduiding",
                    "zaaktype",
                ],
                "next": None,
                "previous": None,
                "count": 1,
                "results": [
                    {
                        "url": None,
                        "zaaktype": {
                            "url": "https://api.catalogi.nl/api/v1/zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
                            "catalogus": CATALOGUS_URL,
                            "catalogusDomein": self.catalogus["domein"],
                            "omschrijving": "zaaktype1",
                            "identificatie": "zaaktype_id_1",
                        },
                        "identificatie": "ZAAK-2022-0000001010",
                        "bronorganisatie": "123456",
                        "omschrijving": "Some zaak description",
                        "vertrouwelijkheidaanduiding": "openbaar",
                        "vaOrder": None,
                        "rollen": [],
                        "startdatum": None,
                        "einddatum": None,
                        "registratiedatum": None,
                        "deadline": "2021-12-31T00:00:00Z",
                        "eigenschappen": [],
                        "status": {
                            "url": None,
                            "statustype": None,
                            "datumStatusGezet": None,
                            "statustoelichting": None,
                        },
                        "toelichting": None,
                        "zaakgeometrie": None,
                    }
                ],
            },
        )

    @requests_mock.Mocker()
    def test_management_dashboard_detail_atomic(self, m):
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        zt = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=self.zaaktype_document1.url,
            identificatie=self.zaaktype_document1.identificatie,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving=self.zaaktype_document1.omschrijving,
            catalogus=self.zaaktype_document1.catalogus,
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={zt['catalogus']}",
            json=paginated_response([zt]),
        )
        user = UserFactory.create()
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

        self.client.force_authenticate(user)
        response = self.client.post(
            self.endpoint,
            data={
                "zaaktype": {
                    "omschrijving": zt["omschrijving"],
                    "catalogus": zt["catalogus"],
                }
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "fields": [
                    "bronorganisatie",
                    "deadline",
                    "identificatie",
                    "omschrijving",
                    "startdatum",
                    "status",
                    "vertrouwelijkheidaanduiding",
                    "zaaktype",
                ],
                "next": None,
                "previous": None,
                "count": 1,
                "results": [
                    {
                        "url": None,
                        "zaaktype": {
                            "url": "https://api.catalogi.nl/api/v1/zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
                            "catalogus": CATALOGUS_URL,
                            "catalogusDomein": self.catalogus["domein"],
                            "omschrijving": "zaaktype1",
                            "identificatie": "zaaktype_id_1",
                        },
                        "identificatie": "ZAAK-2022-0000001010",
                        "bronorganisatie": "123456",
                        "omschrijving": "Some zaak description",
                        "vertrouwelijkheidaanduiding": "openbaar",
                        "vaOrder": None,
                        "rollen": [],
                        "startdatum": None,
                        "einddatum": None,
                        "registratiedatum": None,
                        "deadline": "2021-12-31T00:00:00Z",
                        "eigenschappen": [],
                        "status": {
                            "url": None,
                            "statustype": None,
                            "datumStatusGezet": None,
                            "statustoelichting": None,
                        },
                        "toelichting": None,
                        "zaakgeometrie": None,
                    }
                ],
            },
        )
