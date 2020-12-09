from unittest.mock import patch

from django.conf import settings
from django.http import FileResponse
from django.test import TestCase
from django.urls import reverse

from tablib import Dataset

from zac.accounts.tests.factories import UserFactory

from .factories import ReportFactory


class DownloadViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.report = ReportFactory.create()
        cls.url = reverse("reports:download", kwargs={"pk": cls.report.pk})

    def test_login_required(self):
        response = self.client.get(self.url)

        self.assertRedirects(response, f"{settings.LOGIN_URL}?next={self.url}")

    def test_response_attachment(self):
        user = UserFactory.create()
        self.client.force_login(user)

        with patch("zac.reports.views.export_zaken", return_value=Dataset()):
            response = self.client.get(self.url)

        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        # check that it's a file response
        self.assertIsInstance(response, FileResponse)

    def test_permissions(self):
        raise NotImplementedError("TODO: permissions")
