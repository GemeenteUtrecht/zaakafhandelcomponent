from unittest.mock import patch

from django.conf import settings
from django.urls import reverse

import requests_mock
from elasticsearch_dsl import Index
from rest_framework.test import APITransactionTestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.constants import PermissionObjectTypeChoices
from zac.accounts.tests.factories import (
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.camunda.constants import AssigneeTypeChoices
from zac.core.permissions import zaken_inzien
from zac.core.tests.utils import ClearCachesMixin

from ..documents import ZaakDocument, ZaakTypeDocument
from ..drf_api.serializers import DEFAULT_ES_ZAAKDOCUMENT_FIELDS
from ..models import SearchReport
from .factories import SearchReportFactory
from .utils import ESMixin

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"
CATALOGUS_URL = f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"


class ResponseTests(ClearCachesMixin, ESMixin, APITransactionTestCase):
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
            catalogus_domein=self.catalogus["domein"],
            catalogus=CATALOGUS_URL,
            omschrijving="zaaktype1",
            identicatie="id1",
        )
        self.zaak_document1 = ZaakDocument(
            meta={"id": "a522d30c-6c10-47fe-82e3-e9f524c14ca8"},
            url=f"{ZAKEN_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            zaaktype=self.zaaktype_document1,
            identificatie="ZAAK1",
            bronorganisatie="123456",
            omschrijving="Some zaak description",
            vertrouwelijkheidaanduiding="beperkt_openbaar",
            va_order=16,
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
            catalogus_domein=self.catalogus["domein"],
            catalogus=CATALOGUS_URL,
            omschrijving="zaaktype2",
            identificatie="id2",
        )
        self.zaak_document2 = ZaakDocument(
            meta={"id": "a8c8bc90-defa-4548-bacd-793874c013aa"},
            url="https://api.zaken.nl/api/v1/zaken/a8c8bc90-defa-4548-bacd-793874c013aa",
            zaaktype=self.zaaktype_document2,
            identificatie="ZAAK2",
            bronorganisatie="7890",
            omschrijving="Other description",
            vertrouwelijkheidaanduiding="confidentieel",
            va_order=20,
            rollen=[],
            eigenschappen={"tekst": {"Beleidsveld": "Integratie"}},
            deadline="2021-12-31",
        )
        self.zaak_document2.save()

        zaken = Index(settings.ES_INDEX_ZAKEN)
        zaken.refresh()

    def test_list_reports(self):
        # Mock the zaaktypen that user is allowed to see
        zaaktype_1 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
            catalogus=CATALOGUS_URL,
            omschrijving="zaaktype1",
            identificatie="id1",
        )
        zaaktype_2 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/de7039d7-242a-4186-91c3-c3b49228211a",
            catalogus=CATALOGUS_URL,
            omschrijving="zaaktype2",
            identificatie="id2",
        )
        zaaktypen = [
            factory(ZaakType, zaaktype_1),
            factory(ZaakType, zaaktype_2),
        ]

        user = SuperUserFactory.create()
        self.client.force_authenticate(user=user)

        SearchReportFactory.create(
            query={
                "fields": ["bronorganisatie", "identificatie", "zaaktype"],
                "zaaktype": {
                    "catalogus": CATALOGUS_URL,
                    "omschrijving": "zaaktype1",
                },
            },
        )
        SearchReportFactory.create(
            query={
                "fields": ["bronorganisatie", "identificatie", "zaaktype"],
                "zaaktype": {
                    "catalogus": CATALOGUS_URL,
                    "omschrijving": "zaaktype2",
                },
            },
        )
        endpoint = reverse("searchreport-list")

        with patch(
            "zac.elasticsearch.drf_api.views.get_zaaktypen", return_value=zaaktypen
        ):
            response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)
        results = response.json()
        self.assertEqual(len(results), 2)
        self.assertEqual(
            results[0]["query"],
            {
                "zaaktype": {
                    "omschrijving": "zaaktype1",
                    "catalogus": CATALOGUS_URL,
                },
                "fields": ["bronorganisatie", "identificatie", "zaaktype"],
                "includeClosed": False,
            },
        )
        self.assertEqual(
            results[1]["query"],
            {
                "zaaktype": {
                    "omschrijving": "zaaktype2",
                    "catalogus": CATALOGUS_URL,
                },
                "fields": ["bronorganisatie", "identificatie", "zaaktype"],
                "includeClosed": False,
            },
        )

    @requests_mock.Mocker()
    def test_list_reports_user_only_has_one_zaaktype(self, m):
        # Mock the zaaktypen that user is allowed to see
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        zaaktype_1 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
            catalogus=CATALOGUS_URL,
            omschrijving="zaaktype1",
            identificatie="id1",
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json={"next": None, "count": 1, "previous": None, "results": [zaaktype_1]},
        )

        user = SuperUserFactory.create()
        self.client.force_authenticate(user=user)

        SearchReportFactory.create(
            query={
                "fields": [
                    "bronorganisatie",
                    "identificatie",
                    "zaaktype.url",
                    "zaaktype.catalogus",
                    "zaaktype.omschrijving",
                ],
                "zaaktype": {
                    "catalogus": CATALOGUS_URL,
                    "omschrijving": "zaaktype1",
                },
            },
        )
        SearchReportFactory.create(
            query={
                "fields": [
                    "bronorganisatie",
                    "identificatie",
                    "zaaktype.url",
                    "zaaktype.catalogus",
                    "zaaktype.omschrijving",
                ],
                "zaaktype": {
                    "catalogus": CATALOGUS_URL,
                    "omschrijving": "zaaktype2",
                },
            },
        )
        endpoint = reverse("searchreport-list")

        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)
        results = response.json()
        self.assertEqual(
            results[0]["query"],
            {
                "zaaktype": {
                    "omschrijving": "zaaktype1",
                    "catalogus": CATALOGUS_URL,
                },
                "fields": [
                    "bronorganisatie",
                    "identificatie",
                    "zaaktype.catalogus",
                    "zaaktype.omschrijving",
                    "zaaktype.url",
                ],
                "includeClosed": False,
            },
        )

    @requests_mock.Mocker()
    def test_search_report_detail_all_fields(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        zaaktype_1 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
            catalogus=CATALOGUS_URL,
            omschrijving="zaaktype1",
            identificatie="id1",
        )
        zaaktype_2 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/de7039d7-242a-4186-91c3-c3b49228211a",
            catalogus=CATALOGUS_URL,
            omschrijving="zaaktype2",
            identificatie="id2",
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json={
                "next": None,
                "count": 1,
                "previous": None,
                "results": [zaaktype_1, zaaktype_2],
            },
        )

        user = SuperUserFactory.create()
        self.client.force_authenticate(user=user)

        search_report = SearchReportFactory.create(
            query={
                "fields": DEFAULT_ES_ZAAKDOCUMENT_FIELDS,
            },
        )

        endpoint = reverse("searchreport-results", kwargs={"pk": search_report.pk})

        user = SuperUserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)
        results = response.json()
        self.assertEqual(
            results,
            {
                "fields": [
                    "url",
                    "zaaktype.url",
                    "zaaktype.catalogus",
                    "zaaktype.catalogus_domein",
                    "zaaktype.omschrijving",
                    "zaaktype.identificatie",
                    "identificatie",
                    "bronorganisatie",
                    "omschrijving",
                    "vertrouwelijkheidaanduiding",
                    "va_order",
                    "rollen.url",
                    "rollen.betrokkene_type",
                    "rollen.omschrijving_generiek",
                    "rollen.betrokkene_identificatie.identificatie",
                    "startdatum",
                    "einddatum",
                    "registratiedatum",
                    "deadline",
                    "status.url",
                    "status.statustype",
                    "status.datum_status_gezet",
                    "status.statustoelichting",
                    "toelichting",
                    "zaakgeometrie",
                ],
                "next": None,
                "previous": None,
                "count": 2,
                "results": [
                    {
                        "url": "https://api.zaken.nl/api/v1/zaken/a8c8bc90-defa-4548-bacd-793874c013aa",
                        "zaaktype": {
                            "url": "https://api.catalogi.nl/api/v1/zaaktypen/de7039d7-242a-4186-91c3-c3b49228211a",
                            "catalogus": CATALOGUS_URL,
                            "catalogusDomein": self.catalogus["domein"],
                            "omschrijving": "zaaktype2",
                            "identificatie": "id2",
                        },
                        "identificatie": "ZAAK2",
                        "bronorganisatie": "7890",
                        "omschrijving": "Other description",
                        "vertrouwelijkheidaanduiding": "confidentieel",
                        "vaOrder": 20,
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
                    },
                    {
                        "url": "https://api.zaken.nl/api/v1/zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
                        "zaaktype": {
                            "url": "https://api.catalogi.nl/api/v1/zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
                            "catalogus": CATALOGUS_URL,
                            "catalogusDomein": self.catalogus["domein"],
                            "omschrijving": "zaaktype1",
                            "identificatie": None,
                        },
                        "identificatie": "ZAAK1",
                        "bronorganisatie": "123456",
                        "omschrijving": "Some zaak description",
                        "vertrouwelijkheidaanduiding": "beperkt_openbaar",
                        "vaOrder": 16,
                        "rollen": [
                            {
                                "url": "https://api.zaken.nl/api/v1/rollen/b80022cf-6084-4cf6-932b-799effdcdb26",
                                "betrokkeneType": "organisatorische_eenheid",
                                "omschrijvingGeneriek": None,
                                "betrokkeneIdentificatie": {"identificatie": "123456"},
                            },
                            {
                                "url": "https://api.zaken.nl/api/v1/rollen/de7039d7-242a-4186-91c3-c3b49228211a",
                                "betrokkeneType": "medewerker",
                                "omschrijvingGeneriek": "behandelaar",
                                "betrokkeneIdentificatie": {
                                    "identificatie": "user:some_username"
                                },
                            },
                        ],
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
                    },
                ],
            },
        )

    @requests_mock.Mocker()
    def test_search_report_detail_all_fields_one_zaaktype(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        zaaktype_1 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
            catalogus=CATALOGUS_URL,
            omschrijving="zaaktype1",
            identificatie="id1",
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json={"next": None, "count": 1, "previous": None, "results": [zaaktype_1]},
        )

        user = SuperUserFactory.create()
        self.client.force_authenticate(user=user)

        search_report = SearchReportFactory.create(
            name="Some-report-0",
            query={
                "fields": DEFAULT_ES_ZAAKDOCUMENT_FIELDS,
                "zaaktype": {
                    "catalogus": CATALOGUS_URL,
                    "omschrijving": "zaaktype1",
                },
            },
        )

        endpoint = reverse("searchreport-results", kwargs={"pk": search_report.pk})

        user = SuperUserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)

        results = response.json()
        self.assertEqual(
            results,
            {
                "fields": [
                    "url",
                    "zaaktype.url",
                    "zaaktype.catalogus",
                    "zaaktype.catalogus_domein",
                    "zaaktype.omschrijving",
                    "zaaktype.identificatie",
                    "identificatie",
                    "bronorganisatie",
                    "omschrijving",
                    "vertrouwelijkheidaanduiding",
                    "va_order",
                    "rollen.url",
                    "rollen.betrokkene_type",
                    "rollen.omschrijving_generiek",
                    "rollen.betrokkene_identificatie.identificatie",
                    "startdatum",
                    "einddatum",
                    "registratiedatum",
                    "deadline",
                    "status.url",
                    "status.statustype",
                    "status.datum_status_gezet",
                    "status.statustoelichting",
                    "toelichting",
                    "zaakgeometrie",
                ],
                "next": None,
                "previous": None,
                "count": 1,
                "results": [
                    {
                        "url": "https://api.zaken.nl/api/v1/zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
                        "zaaktype": {
                            "url": "https://api.catalogi.nl/api/v1/zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
                            "catalogus": CATALOGUS_URL,
                            "catalogusDomein": self.catalogus["domein"],
                            "omschrijving": "zaaktype1",
                            "identificatie": None,
                        },
                        "identificatie": "ZAAK1",
                        "bronorganisatie": "123456",
                        "omschrijving": "Some zaak description",
                        "vertrouwelijkheidaanduiding": "beperkt_openbaar",
                        "vaOrder": 16,
                        "rollen": [
                            {
                                "url": "https://api.zaken.nl/api/v1/rollen/b80022cf-6084-4cf6-932b-799effdcdb26",
                                "betrokkeneType": "organisatorische_eenheid",
                                "omschrijvingGeneriek": None,
                                "betrokkeneIdentificatie": {"identificatie": "123456"},
                            },
                            {
                                "url": "https://api.zaken.nl/api/v1/rollen/de7039d7-242a-4186-91c3-c3b49228211a",
                                "betrokkeneType": "medewerker",
                                "omschrijvingGeneriek": "behandelaar",
                                "betrokkeneIdentificatie": {
                                    "identificatie": "user:some_username"
                                },
                            },
                        ],
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
    def test_view_report_detail_some_fields_one_zaaktype(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        zaaktype_1 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
            catalogus=CATALOGUS_URL,
            omschrijving="zaaktype1",
            identificatie="id1",
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json={"next": None, "count": 1, "previous": None, "results": [zaaktype_1]},
        )

        search_report = SearchReportFactory.create(
            name="Some-report-0",
            query={
                "fields": [
                    "bronorganisatie",
                    "identificatie",
                    "zaaktype.url",
                    "zaaktype.catalogus",
                    "zaaktype.omschrijving",
                ],
                "zaaktype": {
                    "catalogus": CATALOGUS_URL,
                    "omschrijving": "zaaktype1",
                },
            },
        )

        endpoint = reverse("searchreport-results", kwargs={"pk": search_report.pk})
        user = SuperUserFactory.create()
        self.client.force_authenticate(user=user)
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)

        results = response.json()
        self.assertEqual(
            results,
            {
                "fields": [
                    "bronorganisatie",
                    "identificatie",
                    "zaaktype.url",
                    "zaaktype.catalogus",
                    "zaaktype.omschrijving",
                ],
                "next": None,
                "previous": None,
                "count": 1,
                "results": [
                    {
                        "url": None,
                        "zaaktype": {
                            "url": f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
                            "catalogus": CATALOGUS_URL,
                            "catalogusDomein": None,
                            "omschrijving": "zaaktype1",
                            "identificatie": None,
                        },
                        "identificatie": "ZAAK1",
                        "bronorganisatie": "123456",
                        "omschrijving": None,
                        "vertrouwelijkheidaanduiding": None,
                        "vaOrder": None,
                        "rollen": [],
                        "startdatum": None,
                        "einddatum": None,
                        "registratiedatum": None,
                        "deadline": None,
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
    def test_create_search_report(self, m):
        endpoint = reverse("searchreport-list")
        user = SuperUserFactory.create()
        self.client.force_authenticate(user=user)
        response = self.client.post(
            endpoint, {"name": "wow-nice-report", "query": {}}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        search_report = SearchReport.objects.get(name="wow-nice-report")
        self.assertEqual(
            search_report.query["fields"],
            [
                "bronorganisatie",
                "deadline",
                "einddatum",
                "identificatie",
                "omschrijving",
                "registratiedatum",
                "rollen.betrokkene_identificatie.identificatie",
                "rollen.betrokkene_type",
                "rollen.omschrijving_generiek",
                "rollen.url",
                "startdatum",
                "status.datum_status_gezet",
                "status.statustoelichting",
                "status.statustype",
                "status.url",
                "toelichting",
                "url",
                "va_order",
                "vertrouwelijkheidaanduiding",
                "zaakgeometrie",
                "zaaktype.catalogus",
                "zaaktype.catalogus_domein",
                "zaaktype.identificatie",
                "zaaktype.omschrijving",
                "zaaktype.url",
            ],
        )
        self.assertEqual(search_report.query["include_closed"], False)


class PermissionTests(ClearCachesMixin, ESMixin, APITransactionTestCase):
    def test_get_list_not_logged_in(self):
        SearchReportFactory.create()
        endpoint = reverse("searchreport-list")
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 403)

    def test_get_list_logged_in(self):
        SearchReportFactory.create()
        search_reports = SearchReport.objects.all()
        endpoint = reverse("searchreport-list")
        user = UserFactory.create()
        self.client.force_authenticate(user)
        with patch(
            "zac.elasticsearch.drf_api.views.SearchReportViewSet.get_queryset",
            return_value=search_reports,
        ):
            response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)

    def test_get_report_not_logged_in(self):
        report = SearchReportFactory.create()
        endpoint = reverse("searchreport-results", kwargs={"pk": report.pk})
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 403)

    def test_get_report_logged_in_no_permission(self):
        report = SearchReportFactory.create()
        endpoint = reverse("searchreport-results", kwargs={"pk": report.pk})
        user = UserFactory.create()
        self.client.force_authenticate(user)
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)
        response = response.json()
        self.assertEqual(response["count"], 0)

    @requests_mock.Mocker()
    def test_get_report_logged_in_with_permission(self, m):
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=CATALOGUS_URL,
            domein="DOME",
        )
        zaaktype_1 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
            catalogus=CATALOGUS_URL,
            omschrijving="zaaktype1",
            identificatie="id1",
        )
        zaaktype_document1 = ZaakTypeDocument(
            url=zaaktype_1["url"],
            catalogus_domein=catalogus["domein"],
            catalogus=zaaktype_1["catalogus"],
            omschrijving=zaaktype_1["omschrijving"],
            identificatie=zaaktype_1["identificatie"],
        )
        zaak_document1 = ZaakDocument(
            meta={"id": "a522d30c-6c10-47fe-82e3-e9f524c14ca8"},
            url=f"{ZAKEN_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            zaaktype=zaaktype_document1,
            identificatie="ZAAK1",
            bronorganisatie="123456",
            omschrijving="Some zaak description",
            vertrouwelijkheidaanduiding="beperkt_openbaar",
            va_order=16,
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
                        "identificatie": "some_username",
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
        zaak_document1.save()
        zaaktype_2 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/de7039d7-242a-4186-91c3-c3b49228211a",
            catalogus=CATALOGUS_URL,
            omschrijving="zaaktype2",
            identificatie="id2",
        )
        zaaktype_document2 = ZaakTypeDocument(
            url=zaaktype_2["url"],
            catalogus_domein=catalogus["domein"],
            catalogus=zaaktype_2["catalogus"],
            omschrijving=zaaktype_2["omschrijving"],
            identificatie=zaaktype_2["identificatie"],
        )
        zaak_document2 = ZaakDocument(
            meta={"id": "a8c8bc90-defa-4548-bacd-793874c013aa"},
            url="https://api.zaken.nl/api/v1/zaken/a8c8bc90-defa-4548-bacd-793874c013aa",
            zaaktype=zaaktype_document2,
            identificatie="ZAAK2",
            bronorganisatie="7890",
            omschrijving="Other description",
            vertrouwelijkheidaanduiding="confidentieel",
            va_order=20,
            rollen=[],
            eigenschappen={"tekst": {"Beleidsveld": "Integratie"}},
            deadline="2021-12-31",
        )
        zaak_document2.save()

        zaken = Index(settings.ES_INDEX_ZAKEN)
        zaken.refresh()

        search_report = SearchReportFactory.create()
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        endpoint = reverse("searchreport-results", kwargs={"pk": search_report.pk})
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)
        response = response.json()
        self.assertEqual(response["count"], 0)

        # Create permission
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=user,
            policy={
                "catalogus": catalogus["domein"],
                "zaaktype_omschrijving": "zaaktype1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
            object_type=PermissionObjectTypeChoices.zaak,
        )
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)
        response = response.json()
        self.assertEqual(response["count"], 1)

        # Create permission
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=user,
            policy={
                "catalogus": catalogus["domein"],
                "zaaktype_omschrijving": "zaaktype2",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
            object_type=PermissionObjectTypeChoices.zaak,
        )

        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)
        response = response.json()
        self.assertEqual(response["count"], 2)
