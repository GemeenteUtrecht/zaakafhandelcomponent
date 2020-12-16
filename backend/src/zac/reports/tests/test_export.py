from unittest.mock import patch

from django.test import TestCase

from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.zaken import ZaakEigenschap

from zac.tests.utils import generate_oas_component
from zgw.models.zrc import Zaak

from ..export import export_zaken
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
    return [
        ZaakEigenschap(url="", eigenschap="", zaak=zaak, naam="eig1", waarde="waarde1"),
        ZaakEigenschap(url="", eigenschap="", zaak=zaak, naam="eig2", waarde="waarde2"),
    ]


class ExportTests(TestCase):
    @patch("zac.reports.export.get_zaak_eigenschappen")
    @patch("zac.reports.export.get_zaak")
    @patch("zac.reports.export.search")
    @patch("zac.reports.export._get_from_catalogus")
    def test_export_zaken_with_status_and_eigenschappen(
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

        # call export function
        result = export_zaken(report)

        # assert result of export
        self.assertEqual(len(result), 2)
        self.assertEqual(
            result.headers,
            [
                "zaaknummer",
                "zaaktype",
                "startdatum",
                "omschrijving",
                "eigenschappen",
                "status",
            ],
        )
        self.assertEqual(result["eigenschappen"][0], "")
        self.assertEqual(result["eigenschappen"][1], "eig1: waarde1\neig2: waarde2")

        self.assertEqual(mock_get_from_catalogus.call_count, 2)
        mock_search.assert_called_once_with(
            zaaktypen=[
                "https://example.com/catalogi/api/v1/zaaktypen/zt1",
                "https://example.com/catalogi/api/v1/zaaktypen/zt2",
            ],
            include_closed=False,
            ordering=["startdatum", "registratiedatum", "identificatie"],
        )
        self.assertEqual(mock_get_zaak.call_count, 2)
        self.assertEqual(mock_get_zaak_eigenschappen.call_count, 2)
