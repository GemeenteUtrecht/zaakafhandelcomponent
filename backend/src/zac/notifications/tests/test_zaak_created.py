from unittest.mock import patch

from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.constants import APITypes

from zac.accounts.models import User
from zac.core.services import _find_zaken
from zac.elasticsearch.documents import ZaakDocument
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests import ServiceFactory
from zac.tests.compat import mock_service_oas_get
from zac.tests.utils import mock_resource_get

from .utils import (
    BRONORGANISATIE,
    CATALOGI_ROOT,
    CATALOGUS_RESPONSE,
    IDENTIFICATIE,
    STATUS_RESPONSE,
    STATUSTYPE_RESPONSE,
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
    "resource": "zaak",
    "resource_url": ZAAK,
    "actie": "create",
    "aanmaakdatum": timezone.now().isoformat(),
    "kenmerken": {
        "bronorganisatie": BRONORGANISATIE,
        "zaaktype": ZAAKTYPE,
        "vertrouwelijkheidaanduiding": "geheim",
    },
}


@requests_mock.Mocker()
class ZaakCreatedTests(ESMixin, APITestCase):
    """
    Test that the appropriate actions happen on zaak-creation notifications.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="notifs")
        cls.ztc = ServiceFactory.create(api_root=CATALOGI_ROOT, api_type=APITypes.ztc)
        cls.zrc = ServiceFactory.create(api_root=ZAKEN_ROOT, api_type=APITypes.zrc)

    def setUp(self):
        super().setUp()
        cache.clear()
        self.client.force_authenticate(user=self.user)

    def test_zaak_created_invalidate_list_cache(self, rm, *mocks):
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_resource_get(rm, ZAAK_RESPONSE)
        mock_resource_get(rm, CATALOGUS_RESPONSE)
        mock_resource_get(rm, ZAAKTYPE_RESPONSE)
        mock_resource_get(rm, STATUS_RESPONSE)
        mock_resource_get(rm, STATUSTYPE_RESPONSE)

        zrc_client = self.zrc.build_client()
        url = reverse("notifications:callback")

        matrix = [
            {},
            {"zaaktype": ZAAKTYPE},
            {"identificatie": IDENTIFICATIE},
            {"bronorganisatie": BRONORGANISATIE},
            {"zaaktype": ZAAKTYPE, "identificatie": IDENTIFICATIE},
            {"zaaktype": ZAAKTYPE, "bronorganisatie": BRONORGANISATIE},
            {"identificatie": IDENTIFICATIE, "bronorganisatie": BRONORGANISATIE},
            {
                "zaaktype": ZAAKTYPE,
                "identificatie": IDENTIFICATIE,
                "bronorganisatie": BRONORGANISATIE,
            },
        ]

        for kwargs in matrix:
            with self.subTest(kwargs=kwargs):
                with patch(
                    "zac.core.services.get_paginated_results", return_value=[]
                ) as m:
                    # populate cache
                    _find_zaken(zrc_client, **kwargs)

                    response = self.client.post(url, NOTIFICATION)
                    self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

                    # second call should re-fetch (cache invalidated)
                    _find_zaken(zrc_client, **kwargs)
                    self.assertEqual(m.call_count, 2)

    def test_max_va_cache_key(self, rm, *mocks):
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_resource_get(rm, ZAAK_RESPONSE)
        mock_resource_get(rm, CATALOGUS_RESPONSE)
        mock_resource_get(rm, ZAAKTYPE_RESPONSE)
        mock_resource_get(rm, STATUS_RESPONSE)
        mock_resource_get(rm, STATUSTYPE_RESPONSE)

        zrc_client = self.zrc.build_client()
        url = reverse("notifications:callback")

        matrix = [
            {"zaaktype": ZAAKTYPE, "max_va": "geheim"},
            {"zaaktype": ZAAKTYPE, "max_va": "zeer_geheim"},
        ]

        for kwargs in matrix:
            with self.subTest(kwargs=kwargs):
                with patch(
                    "zac.core.services.get_paginated_results", return_value=[]
                ) as m:
                    # populate cache
                    _find_zaken(zrc_client, **kwargs)

                    response = self.client.post(url, NOTIFICATION)
                    self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

                    # second call should re-fetch (cache invalidated)
                    _find_zaken(zrc_client, **kwargs)
                    self.assertEqual(m.call_count, 2)

    def test_zaak_created_indexed_in_es(self, rm, *mocks):
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_resource_get(rm, ZAAK_RESPONSE)
        mock_resource_get(rm, CATALOGUS_RESPONSE)
        mock_resource_get(rm, ZAAKTYPE_RESPONSE)
        mock_resource_get(rm, STATUS_RESPONSE)
        mock_resource_get(rm, STATUSTYPE_RESPONSE)

        url = reverse("notifications:callback")

        zaak_document = ZaakDocument.get(
            id="f3ff2713-2f53-42ff-a154-16842309ad60", ignore=404
        )
        self.assertIsNone(zaak_document)

        response = self.client.post(url, NOTIFICATION)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        zaak_document = ZaakDocument.get(id="f3ff2713-2f53-42ff-a154-16842309ad60")
        self.assertIsNotNone(zaak_document)
        self.assertEqual(zaak_document.bronorganisatie, BRONORGANISATIE)
        self.assertEqual(zaak_document.zaaktype["url"], ZAAKTYPE)
