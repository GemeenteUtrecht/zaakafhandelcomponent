from unittest.mock import patch

from django.conf import settings
from django.http import FileResponse
from django.test import TestCase
from django.urls import reverse, reverse_lazy

from tablib import Dataset
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType

from zac.accounts.tests.factories import SuperUserFactory, UserFactory
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import generate_oas_component

from .factories import ReportFactory


class DownloadViewTests(ClearCachesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.report = ReportFactory.create()
        cls.url = reverse("reports:download", kwargs={"pk": cls.report.pk})

    def test_login_required(self):
        response = self.client.get(self.url)

        self.assertRedirects(response, f"{settings.LOGIN_URL}?next={self.url}")

    def test_response_attachment(self):
        user = SuperUserFactory.create()
        self.client.force_login(user)

        with patch("zac.reports.views.export_zaken", return_value=Dataset()):
            response = self.client.get(self.url)

        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        # check that it's a file response
        self.assertIsInstance(response, FileResponse)

    @patch("zac.reports.views.export_zaken", return_value=Dataset())
    @patch("zac.reports.rules.get_zaaktypen")
    def test_permissions(self, mock_get_zaaktypen, *args):
        user = UserFactory.create()
        self.client.force_login(user)
        report1 = ReportFactory.create(zaaktypen=["zt1", "zt2"])
        report2 = ReportFactory.create(zaaktypen=["zt1"])
        zaaktype1 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"https://example.com/catalogi/api/v1/zaaktypen/zt1",
            identificatie="zt1",
        )
        mock_get_zaaktypen.return_value = factory(ZaakType, [zaaktype1])
        download_url1 = reverse("reports:download", kwargs={"pk": report1.pk})
        download_url2 = reverse("reports:download", kwargs={"pk": report2.pk})

        with self.subTest(report=report1):
            response = self.client.get(download_url1)

            self.assertEqual(response.status_code, 403)

        with self.subTest(report=report2):
            response = self.client.get(download_url2)

            self.assertEqual(response.status_code, 200)


class ListViewTests(ClearCachesMixin, TestCase):
    url = reverse_lazy("reports:report-list")

    def test_login_required(self):
        response = self.client.get(self.url)

        self.assertRedirects(response, f"{settings.LOGIN_URL}?next={self.url}")

    def test_list_page(self):
        user = SuperUserFactory.create()
        self.client.force_login(user)
        report = ReportFactory.create()

        response = self.client.get(self.url)

        download_url = reverse("reports:download", kwargs={"pk": report.pk})
        self.assertContains(response, download_url)

    @patch("zac.reports.views.get_zaaktypen")
    def test_limit_to_accessible_zaaktypen(self, mock_get_zaaktypen):
        user = UserFactory.create()
        self.client.force_login(user)
        report1 = ReportFactory.create(zaaktypen=["zt1", "zt2"])
        report2 = ReportFactory.create(zaaktypen=["zt1"])
        zaaktype1 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"https://example.com/catalogi/api/v1/zaaktypen/zt1",
            identificatie="zt1",
        )
        mock_get_zaaktypen.return_value = factory(ZaakType, [zaaktype1])

        response = self.client.get(self.url)

        download_url1 = reverse("reports:download", kwargs={"pk": report1.pk})
        download_url2 = reverse("reports:download", kwargs={"pk": report2.pk})
        self.assertNotContains(response, download_url1)
        self.assertContains(response, download_url2)
