from dataclasses import asdict

from django.core.cache import cache, caches

import requests_mock
from rest_framework.test import APITransactionTestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.zaken import Rol, Zaak
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.core.cache import invalidate_rollen_cache
from zac.core.services import fetch_rol, get_rollen
from zac.core.tests.utils import ClearCachesMixin

ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"
ZAAK_URL = f"{ZAKEN_ROOT}zaken/482de5b2-4779-4b29-b84f-add888352182"


@requests_mock.Mocker()
class TestCacheRollen(ClearCachesMixin, APITransactionTestCase):
    def test_get_rollen_cache(self, m):
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        rollen = [
            generate_oas_component(
                "zrc",
                "schemas/Rol",
                zaak=ZAAK_URL,
                betrokkene_identificatie={
                    "identificatie": "123456",
                    "voorletters": "M Y",
                    "achternaam": "Surname",
                    "voorvoegsel_achternaam": "",
                },
            )
        ]
        paginated_response = {
            "count": 0,
            "next": None,
            "previous": None,
            "results": rollen,
        }
        m.get(f"{ZAKEN_ROOT}rollen?zaak={ZAAK_URL}", json=paginated_response)

        # Make sure rollen arent cached
        _cache = caches["request"]
        self.assertFalse(f"rollen:{ZAAK_URL}" in _cache)
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
        )

        # Make call
        rollen = get_rollen(factory(Zaak, zaak))

        # Assert rollen are now in cache
        self.assertTrue(f"rollen:{ZAAK_URL}" in _cache)
        self.assertEqual(rollen, _cache.get(f"rollen:{ZAAK_URL}"))

    def test_fetch_rol_cache(self, m):
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        rol = generate_oas_component(
            "zrc",
            "schemas/Rol",
            url=f"{ZAKEN_ROOT}rollen/482de5b2-4779-4b29-b84f-add888352183",
            betrokkene_identificatie={
                "identificatie": "123456",
                "voorletters": "M Y",
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

    def test_invalidate_get_rollen_cache(self, m):
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        rollen = [
            generate_oas_component(
                "zrc",
                "schemas/Rol",
                zaak=ZAAK_URL,
                betrokkene_identificatie={
                    "identificatie": "123456",
                    "voorletters": "M Y",
                    "achternaam": "Surname",
                    "voorvoegsel_achternaam": "",
                },
                omschrijving="ene-rol",
            )
        ]
        paginated_response = {
            "count": 0,
            "next": None,
            "previous": None,
            "results": rollen,
        }
        m.get(f"{ZAKEN_ROOT}rollen?zaak={ZAAK_URL}", json=paginated_response)

        # Make sure rollen arent cached
        _cache = caches["request"]
        self.assertFalse(f"rollen:{ZAAK_URL}" in _cache)
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
        )
        zaak = factory(Zaak, zaak)

        # Make call
        old_rollen = get_rollen(zaak)

        # Assert rollen are now in cache
        self.assertTrue(f"rollen:{ZAAK_URL}" in _cache)
        self.assertEqual(old_rollen, _cache.get(f"rollen:{ZAAK_URL}"))

        # Mock a different response:
        new_rollen = [
            generate_oas_component(
                "zrc",
                "schemas/Rol",
                zaak=ZAAK_URL,
                betrokkene_identificatie={
                    "identificatie": "123456",
                    "voorletters": "M Y",
                    "achternaam": "Surname",
                    "voorvoegsel_achternaam": "",
                },
                omschrijving="andere-rol",
            )
        ]
        new_rollen_objs = []
        for rol in new_rollen:
            rol = factory(Rol, rol)
            rol.zaak = zaak
            new_rollen_objs.append(rol)

        paginated_response = {
            "count": 0,
            "next": None,
            "previous": None,
            "results": new_rollen,
        }
        m.get(f"{ZAKEN_ROOT}rollen?zaak={ZAAK_URL}", json=paginated_response)
        invalidate_rollen_cache(zaak)

        # Assert rollen are still cached...
        self.assertTrue(f"rollen:{ZAAK_URL}" in _cache)
        # ... but return the new rollen
        cached_rol = _cache.get(f"rollen:{ZAAK_URL}")[0]
        new_rol = new_rollen_objs[0]
        self.assertEqual(asdict(cached_rol), asdict(new_rol))

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
                "voorletters": "M Y",
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

        # Mock request for get_rollen in invalidate_rollen_cache
        paginated_response = {
            "count": 0,
            "next": None,
            "previous": None,
            "results": [rol],
        }
        m.get(f"{ZAKEN_ROOT}rollen?zaak={ZAAK_URL}", json=paginated_response)

        # Create zaak
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
        )
        zaak = factory(Zaak, zaak)

        # Invalidate cache
        invalidate_rollen_cache(zaak)

        # Make sure rol isnt cached anymore
        self.assertFalse(f"rol:{rol['url']}" in cache)
