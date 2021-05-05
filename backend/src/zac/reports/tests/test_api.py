from unittest.mock import patch

from django.urls import reverse

from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import Eigenschap
from zgw_consumers.api_models.zaken import ZaakEigenschap
from zgw_consumers.test import generate_oas_component

from zac.accounts.constants import PermissionObjectType
from zac.accounts.tests.factories import (
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.reports.api.permissions import rapport_inzien
from zgw.models.zrc import Zaak

from .factories import ReportFactory


def _get_from_catalogus(resource: str, catalogus="", identificatie: str = ""):
    zaaktype = generate_oas_component(
        "ztc",
        "schemas/ZaakType",
        url=f"https://example.com/catalogi/api/v1/zaaktypen/{identificatie}",
        omschrijving=identificatie,
        identificatie=identificatie,
    )
    return [zaaktype]


def get_zaak(zaak_url: str):
    ZAAKTYPEN = {
        "https://example.com/zaken/api/v1/zaken/123": "https://example.com/catalogi/api/v1/zaaktypen/zt1",
        "https://example.com/zaken/api/v1/zaken/456": "https://example.com/catalogi/api/v1/zaaktypen/zt2",
    }
    zaak = generate_oas_component(
        "zrc",
        "schemas/Zaak",
        url=zaak_url,
        identificatie=zaak_url.split("/")[-1],
        zaaktype=ZAAKTYPEN[zaak_url],
    )
    return factory(Zaak, zaak)


def get_zaak_eigenschappen(zaak: Zaak):
    if zaak.identificatie == "123":
        return []

    eigenschapspec = generate_oas_component(
        "ztc",
        "schemas/EigenschapSpecificatie",
        formaat="tekst",
    )
    eigenschap = generate_oas_component(
        "ztc", "schemas/Eigenschap", specificatie=eigenschapspec
    )
    eigenschap = factory(Eigenschap, eigenschap)

    return [
        ZaakEigenschap(
            url="", eigenschap=eigenschap, zaak=zaak, naam="eig1", waarde="waarde1"
        ),
        ZaakEigenschap(
            url="", eigenschap=eigenschap, zaak=zaak, naam="eig2", waarde="waarde2"
        ),
    ]


class ResponseTests(APITestCase):
    def test_list_reports(self):
        user = SuperUserFactory.create()
        self.client.force_authenticate(user=user)

        ReportFactory.create_batch(5)
        endpoint = reverse("report-api-list")
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 5)

    @patch("zac.reports.export.get_zaak_eigenschappen")
    @patch("zac.reports.export.get_zaak")
    @patch("zac.reports.export.search")
    @patch("zac.reports.export._get_from_catalogus")
    def test_view_report(
        self,
        mock_get_from_catalogus,
        mock_search,
        mock_get_zaak,
        mock_get_zaak_eigenschappen,
    ):
        # set up test data and mocks
        report = ReportFactory.create(zaaktypen=["zt1", "zt2"])
        mock_get_from_catalogus.side_effect = _get_from_catalogus
        mock_search.return_value = [
            "https://example.com/zaken/api/v1/zaken/123",
            "https://example.com/zaken/api/v1/zaken/456",
        ]
        zaak = get_zaak
        mock_get_zaak.side_effect = get_zaak
        mock_get_zaak_eigenschappen.side_effect = get_zaak_eigenschappen

        endpoint = reverse("report-api-download", kwargs={"pk": report.pk})

        user = SuperUserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["next"], None)
        self.assertEqual(data["previous"], None)
        self.assertTrue("results" in data)
        self.assertEqual(len(data["results"]), 2)
        self.assertTrue("eigenschappen" in data["results"][0])
        self.assertTrue("identificatie" in data["results"][0])
        self.assertTrue("omschrijving" in data["results"][0])
        self.assertTrue("startdatum" in data["results"][0])
        self.assertTrue("status" in data["results"][0])
        self.assertTrue("zaaktypeOmschrijving" in data["results"][0])

    @patch("zac.reports.export.get_zaak_eigenschappen")
    @patch("zac.reports.export.get_zaak")
    @patch("zac.reports.export.search")
    @patch("zac.reports.export._get_from_catalogus")
    def test_view_report_ordering(
        self,
        mock_get_from_catalogus,
        mock_search,
        mock_get_zaak,
        mock_get_zaak_eigenschappen,
    ):
        # set up test data and mocks
        report = ReportFactory.create(zaaktypen=["zt1", "zt2"])
        mock_get_from_catalogus.side_effect = _get_from_catalogus
        mock_search.return_value = [
            "https://example.com/zaken/api/v1/zaken/123",
            "https://example.com/zaken/api/v1/zaken/456",
        ]
        mock_get_zaak.side_effect = get_zaak
        mock_get_zaak_eigenschappen.side_effect = get_zaak_eigenschappen

        endpoint = (
            reverse("report-api-download", kwargs={"pk": report.pk})
            + "?ordering=-zaaktype_omschrijving"
        )

        user = SuperUserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["results"][0]["zaaktypeOmschrijving"], "zt2")
        self.assertTrue(data["results"][1]["zaaktypeOmschrijving"], "zt1")


class PermissionTests(APITestCase):
    def test_get_list_not_logged_in(self):
        ReportFactory.create()
        endpoint = reverse("report-api-list")
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 403)

    def test_get_list_logged_in(self):
        ReportFactory.create()
        endpoint = reverse("report-api-list")
        user = UserFactory.create()
        self.client.force_authenticate(user)
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)

    def test_get_report_not_logged_in(self):
        report = ReportFactory.create(zaaktypen=["zt1", "zt2"])
        endpoint = reverse("report-api-download", kwargs={"pk": report.pk})
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 403)

    def test_get_report_logged_in_no_permission(self):
        report = ReportFactory.create(zaaktypen=["zt1", "zt2"])
        endpoint = reverse("report-api-download", kwargs={"pk": report.pk})
        user = UserFactory.create()
        self.client.force_authenticate(user)
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 403)

    @patch("zac.reports.export.get_zaak_eigenschappen")
    @patch("zac.reports.export.get_zaak")
    @patch("zac.reports.export.search")
    @patch("zac.reports.export._get_from_catalogus")
    def test_get_report_logged_in_with_permission(
        self,
        mock_get_from_catalogus,
        mock_search,
        mock_get_zaak,
        mock_get_zaak_eigenschappen,
    ):
        # set up test data and mocks
        report = ReportFactory.create(zaaktypen=["zt1", "zt2"])
        mock_get_from_catalogus.side_effect = _get_from_catalogus
        mock_search.return_value = [
            "https://example.com/zaken/api/v1/zaken/123",
            "https://example.com/zaken/api/v1/zaken/456",
        ]
        zaak = get_zaak
        mock_get_zaak.side_effect = get_zaak
        mock_get_zaak_eigenschappen.side_effect = get_zaak_eigenschappen

        endpoint = reverse("report-api-download", kwargs={"pk": report.pk})

        user = UserFactory.create()
        self.client.force_authenticate(user=user)

        # Create permission
        BlueprintPermissionFactory.create(
            permission=rapport_inzien.name,
            for_user=user,
            policy={
                "zaaktypen": ["zt1", "zt2"],
            },
            object_type=PermissionObjectType.report,
        )

        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)
