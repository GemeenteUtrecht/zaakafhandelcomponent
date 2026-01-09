from unittest.mock import patch

from django.core.cache import cache

import requests_mock
from rest_framework.test import APITransactionTestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.zaken import Zaak
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.core.cache import invalidate_rollen_cache
from zac.core.services import fetch_rol
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.compat import generate_oas_component, mock_service_oas_get

ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"
ZAAK_URL = f"{ZAKEN_ROOT}zaken/482de5b2-4779-4b29-b84f-add888352182"


@requests_mock.Mocker()
class TestCacheRollen(ClearCachesMixin, APITransactionTestCase):
    def test_fetch_rol_cache(self, m):
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        rol = generate_oas_component(
            "zrc",
            "schemas/Rol",
            url=f"{ZAKEN_ROOT}rollen/482de5b2-4779-4b29-b84f-add888352183",
            betrokkene_identificatie={
                "identificatie": "123456",
                "voorletters": "M.Y.",
                "achternaam": "Surname",
                "voorvoegsel_achternaam": "",
            },
        )

        m.get(rol["url"], json=rol)

        # Make sure rol isnt cached
        self.assertFalse(f"rol:{rol['url']}" in cache)

        # Make call
        fetched_rol = fetch_rol(rol["url"])

        # Assert rol is now cached
        self.assertTrue(f"rol:{rol['url']}" in cache)
        self.assertEqual(fetched_rol, cache.get(f"rol:{rol['url']}"))

    def test_invalidate_fetch_rol_cache(self, m):
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        rol = generate_oas_component(
            "zrc",
            "schemas/Rol",
            zaak=ZAAK_URL,
            url=f"{ZAKEN_ROOT}rollen/482de5b2-4779-4b29-b84f-add888352183",
            betrokkene_identificatie={
                "identificatie": "123456",
                "voorletters": "M.Y.",
                "achternaam": "Surname",
                "voorvoegsel_achternaam": "",
            },
        )

        m.get(rol["url"], json=rol)

        # Make sure rol isnt cached
        self.assertFalse(f"rol:{rol['url']}" in cache)

        # Make call
        fetched_rol = fetch_rol(rol["url"])

        # Assert rol is now cached
        self.assertTrue(f"rol:{rol['url']}" in cache)
        self.assertEqual(fetched_rol, cache.get(f"rol:{rol['url']}"))

        # Create zaak
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
        )
        zaak = factory(Zaak, zaak)

        # Invalidate cache
        invalidate_rollen_cache(zaak, rol_urls=[rol["url"]])

        # Make sure rol isnt cached anymore
        self.assertFalse(f"rol:{rol['url']}" in cache)

        with self.subTest(
            "Regression test in case rol_urls is None and redis cache is true"
        ):
            with patch("zac.core.cache.is_redis_cache", return_value=True):
                with patch("zac.core.cache.cache") as mock_cache:
                    invalidate_rollen_cache(zaak, rol_urls=None)
                    mock_cache.delete_pattern.assert_called()
