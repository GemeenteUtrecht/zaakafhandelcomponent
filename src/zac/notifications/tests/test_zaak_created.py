from unittest.mock import patch

from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.models import APITypes, Service

from zac.accounts.models import User
from zac.core.services import _find_zaken

from .utils import mock_service_oas_get

ZAAKTYPE = "https://some.ztc.nl/api/v1/zaaktypen/ad4573d0-4d99-4e90-a05c-e08911e8673d"

IDENTIFICATIE = "ZAAK-123"
BRONORGANISATIE = "123456782"

NOTIFICATION = {
    "kanaal": "zaken",
    "hoofdObject": "https://some.zrc.nl/api/v1/zaken/f3ff2713-2f53-42ff-a154-16842309ad60",
    "resource": "zaak",
    "resourceUrl": "https://some.zrc.nl/api/v1/zaken/f3ff2713-2f53-42ff-a154-16842309ad60",
    "actie": "create",
    "aanmaakdatum": timezone.now().isoformat(),
    "kenmerken": {
        "bronorganisatie": BRONORGANISATIE,
        "zaaktype": ZAAKTYPE,
        "vertrouwelijkheidaanduiding": "geheim",
    },
}


def mock_zaak_retrieve(mocker):
    mocker.get(
        "https://some.zrc.nl/api/v1/zaken/f3ff2713-2f53-42ff-a154-16842309ad60",
        json={
            "url": "https://some.zrc.nl/api/v1/zaken/f3ff2713-2f53-42ff-a154-16842309ad60",
            "identificatie": IDENTIFICATIE,
            "bronorganisatie": BRONORGANISATIE,
            "zaaktype": ZAAKTYPE,
        },
    )


@requests_mock.Mocker()
class ZaakCreatedTests(APITestCase):
    """
    Test that the appropriate actions happen on zaak-creation notifications.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="notifs")
        cls.ztc = Service.objects.create(
            api_root="https://some.ztc.nl/api/v1/", api_type=APITypes.ztc
        )
        cls.zrc = Service.objects.create(
            api_root="https://some.zrc.nl/api/v1/", api_type=APITypes.zrc
        )

    def setUp(self):
        super().setUp()

        cache.clear()
        self.client.force_authenticate(user=self.user)

    def test_zaak_created_invalidate_list_cache(self, rm):
        mock_service_oas_get(rm, "https://some.zrc.nl/api/v1/", "zaken")
        mock_zaak_retrieve(rm)
        zrc_client = self.zrc.build_client()
        path = reverse("notifications:callback")

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
                    # call to populate cache
                    _find_zaken(zrc_client, **kwargs)

                    response = self.client.post(path, NOTIFICATION)
                    self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

                    # second call should not hit the cache
                    _find_zaken(zrc_client, **kwargs)
                    self.assertEqual(m.call_count, 2)
