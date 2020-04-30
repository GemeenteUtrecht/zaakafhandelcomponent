from django.urls import reverse_lazy

import requests_mock
from django_webtest import WebTest
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.accounts.tests.factories import UserFactory
from zac.tests.utils import generate_oas_component, mock_service_oas_get

from .utils import ClearCachesMixin

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"


@requests_mock.Mocker()
class ZaakListTests(ClearCachesMixin, WebTest):

    url = reverse_lazy("core:index")

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory.create()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

    def test_list_zaken_no_perms(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        zaaktype = generate_oas_component("ztc", "schemas/ZaakType")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json={"count": 1, "previous": None, "next": None, "results": [zaaktype],},
        )

        response = self.app.get(self.url, user=self.user)

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.context["filter_form"].fields["zaaktypen"].choices, [],
        )
        self.assertEqual(response.context["zaken"], [])

        # verify amount of API calls - 1 to fetch the schema, 1 to get the zaaktypen
        self.assertEqual(len(m.request_history), 2)
