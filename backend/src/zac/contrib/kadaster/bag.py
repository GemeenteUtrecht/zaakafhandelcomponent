from typing import Any, Dict

from django.conf import settings

from zgw_consumers.concurrent import parallel

from zac.core.utils import A_DAY
from zac.utils.decorators import cache
from zac.utils.http import get_session

from .models import KadasterConfig


class Bag:
    def __init__(self):
        config = KadasterConfig.get_solo()
        self.url = config.service.api_root
        self.headers = config.service.get_auth_header(self.url)
        self._session = get_session()

    def retrieve(self, url: str, *args, **kwargs):
        kwargs.setdefault("timeout", settings.REQUESTS_DEFAULT_TIMEOUT)
        response = self._session.get(url, headers=self.headers, *args, **kwargs)
        response.raise_for_status()
        return response.json()

    def get(self, path: str, *args, **kwargs):
        kwargs.setdefault("timeout", settings.REQUESTS_DEFAULT_TIMEOUT)
        full_url = f"{self.url}{path}"
        response = self._session.get(full_url, headers=self.headers, *args, **kwargs)
        response.raise_for_status()
        return response.json()


class LocationServer:
    def __init__(self):
        config = KadasterConfig.get_solo()
        self.url = config.locatieserver
        self._session = get_session()

    def get(self, path: str, *args, **kwargs):
        kwargs.setdefault("timeout", settings.REQUESTS_DEFAULT_TIMEOUT)
        full_url = f"{self.url}{path}"
        response = self._session.get(full_url, *args, **kwargs)
        response.raise_for_status()
        return response.json()

    def suggest(self, query: dict):
        return self.get("suggest", params=query)

    def lookup(self, some_id: str):
        resp_data = self.get("lookup", params={"id": some_id})
        return resp_data["response"]


@cache("openbareruimte:{url}", timeout=A_DAY)
def _fetch_openbare_ruimte(bag: Bag, url: str) -> dict:
    return bag.retrieve(url)


@cache("woonplaats:{url}", timeout=A_DAY)
def _fetch_woonplaats(bag: Bag, url: str) -> dict:
    return bag.retrieve(url)


@cache("nummeraanduiding:{url}", timeout=A_DAY)
def _fetch_adres(bag: Bag, url: str) -> dict:
    _hoofdadres = bag.retrieve(url)
    _openbare_ruimte = _fetch_openbare_ruimte(
        bag, _hoofdadres["_links"]["bijbehorendeOpenbareRuimte"]["href"]
    )
    _woonplaats = _fetch_woonplaats(
        bag, _openbare_ruimte["_links"]["bijbehorendeWoonplaats"]["href"]
    )
    return {
        "huisnummer": _hoofdadres["huisnummer"],
        "huisletter": _hoofdadres.get("huisletter", ""),
        "postcode": _hoofdadres.get("postcode", ""),
        "or_naam": _openbare_ruimte["naam"],
        "woonplaats": _woonplaats["naam"],
    }


@cache("pand:{url}", timeout=A_DAY)
def fetch_pand(url: str) -> Dict[str, Any]:
    bag = Bag()

    pand = bag.retrieve(url)

    _verblijfsobjecten = bag.retrieve(pand["_links"]["verblijfsobjecten"]["href"])[
        "_embedded"
    ]["verblijfsobjecten"]

    def fetch_adres(vo: dict) -> dict:
        return _fetch_adres(bag, vo["_links"]["hoofdadres"]["href"])

    with parallel(max_workers=settings.MAX_WORKERS) as executor:
        adressen = list(executor.map(fetch_adres, _verblijfsobjecten))

    verblijfsobjecten = [
        {
            "url": vo["_links"]["self"]["href"],
            "identificatiecode": vo["identificatiecode"],
            "oppervlakte": vo["oppervlakte"],
            "status": vo["status"],
        }
        for vo in _verblijfsobjecten
    ]

    return {
        "url": pand["_links"]["self"]["href"],
        "identificatiecode": pand["identificatiecode"],
        "oorspronkelijkBouwjaar": pand["oorspronkelijkBouwjaar"],
        "status": pand["status"],
        "geometry": pand["_embedded"]["geometrie"],
        "geldigVoorkomen": pand["_embedded"]["geldigVoorkomen"],
        "verblijfsobjecten": verblijfsobjecten,
        "adressen": adressen,
    }


@cache("verblijfsobject:{url}", timeout=A_DAY)
def fetch_verblijfsobject(url: str) -> Dict[str, Any]:
    bag = Bag()

    verblijfsobject = bag.retrieve(url)
    adres = _fetch_adres(bag, verblijfsobject["_links"]["hoofdadres"]["href"])

    return {
        "url": verblijfsobject["_links"]["self"]["href"],
        "identificatiecode": verblijfsobject["identificatiecode"],
        "oppervlakte": verblijfsobject["oppervlakte"],
        "status": verblijfsobject["status"],
        "geometry": verblijfsobject["_embedded"]["geometrie"],
        "adres": adres,
    }
