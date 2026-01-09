from unittest.mock import patch

from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.accounts.models import User
from zac.core.services import find_zaak, get_zaak
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.compat import mock_service_oas_get
from zac.tests.utils import mock_resource_get
from zgw.models import Zaak

from .utils import (
    BRONORGANISATIE,
    CATALOGI_ROOT,
    CATALOGUS_RESPONSE,
    IDENTIFICATIE,
    ZAAK,
    ZAAK_RESPONSE,
    ZAAKTYPE,
    ZAAKTYPE_RESPONSE,
    ZAKEN_ROOT,
)

# UPDATED: snake_case keys
NOTIFICATION = {
    "kanaal": "zaken",
    "hoofd_object": ZAAK,
    "resource": "resultaat",
    "resource_url": f"{ZAKEN_ROOT}resultaten/f3ff2713-2f53-42ff-a154-16842309ad60",
    "actie": "create",
    "aanmaakdatum": timezone.now().isoformat(),
    "kenmerken": {
        "bronorganisatie": BRONORGANISATIE,
        "zaaktype": ZAAKTYPE,
        "vertrouwelijkheidaanduiding": "geheim",
    },
}


@requests_mock.Mocker()
class ResultaatCreatedTests(ESMixin, APITestCase):
    """
    Test that the appropriate actions happen on resultaat-creation notifications.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="notifs")
        cls.ztc = Service.objects.create(api_root=CATALOGI_ROOT, api_type=APITypes.ztc)
        cls.zrc = Service.objects.create(api_root=ZAKEN_ROOT, api_type=APITypes.zrc)

    def setUp(self):
        super().setUp()
        cache.clear()
        self.client.force_authenticate(user=self.user)

    def test_find_zaak_resultaat_created(self, rm):
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_resource_get(rm, ZAAK_RESPONSE)
        mock_resource_get(rm, ZAAKTYPE_RESPONSE)
        mock_resource_get(rm, CATALOGUS_RESPONSE)

        url = reverse("notifications:callback")

        with patch(
            "zac.core.services.get_paginated_results", return_value=[ZAAK_RESPONSE]
        ) as m:
            with patch(
                "zac.core.services.get_zaak", return_value=factory(Zaak, ZAAK_RESPONSE)
            ) as m_get_zaak:
                # call to populate cache
                find_zaak(BRONORGANISATIE, IDENTIFICATIE)

                response = self.client.post(url, NOTIFICATION)
                self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

                # second call should not hit the cache but it should hit get_zaak
                find_zaak(BRONORGANISATIE, IDENTIFICATIE)
                self.assertEqual(m.call_count, 1)
                find_zaak(BRONORGANISATIE, IDENTIFICATIE)
                self.assertEqual(m_get_zaak.call_count, 1)

    def test_get_zaak_resultaat_created(self, rm):
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_resource_get(rm, ZAAK_RESPONSE)
        mock_resource_get(rm, ZAAKTYPE_RESPONSE)
        mock_resource_get(rm, CATALOGUS_RESPONSE)

        url = reverse("notifications:callback")

        matrix = [
            {"zaak_uuid": "f3ff2713-2f53-42ff-a154-16842309ad60"},
            {"zaak_url": ZAAK},
            {"zaak_uuid": "f3ff2713-2f53-42ff-a154-16842309ad60", "zaak_url": ZAAK},
        ]

        for kwargs in matrix:
            with self.subTest(**kwargs):
                # call to populate cache
                get_zaak(**kwargs)
                self.assertEqual(rm.last_request.url, ZAAK)
                first_retrieve = rm.last_request

                response = self.client.post(url, NOTIFICATION)
                self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

                num_calls_before = len(rm.request_history)

                # second call should re-fetch (cache was invalidated)
                get_zaak(**kwargs)

                self.assertEqual(rm.last_request.url, ZAAK)
                self.assertNotEqual(rm.last_request, first_retrieve)
                self.assertEqual(len(rm.request_history), num_calls_before + 1)
