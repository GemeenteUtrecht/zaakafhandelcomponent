from typing import Any, Dict

import requests

from zac.utils.decorators import cache

from .models import KadasterConfig


class Bag:
    def __init__(self):
        config = KadasterConfig.get_solo()
        self.url = config.bag_api
        self.headers = {"X-Api-Key": config.api_key}

    def retrieve(self, url: str, *args, **kwargs):
        response = requests.get(url, headers=self.headers, *args, **kwargs)
        response.raise_for_status()
        return response.json()

    def get(self, path: str, *args, **kwargs):
        full_url = f"{self.url}{path}"
        response = requests.get(full_url, headers=self.headers, *args, **kwargs)
        response.raise_for_status()
        return response.json()


@cache("pand:{url}", timeout=60 * 60 * 24)
def fetch_pand(url: str) -> Dict[str, Any]:
    bag = Bag()

    pand = bag.retrieve(url)

    adressen = []

    _verblijfsobjecten = bag.retrieve(pand["_links"]["verblijfsobjecten"]["href"])[
        "_embedded"
    ]["verblijfsobjecten"]

    # TODO: parallelize
    for vo in _verblijfsobjecten:
        _hoofdadres = bag.retrieve(vo["_links"]["hoofdadres"]["href"])
        _openbare_ruimte = bag.retrieve(
            _hoofdadres["_links"]["bijbehorendeOpenbareRuimte"]["href"]
        )
        _woonplaats = bag.retrieve(
            _openbare_ruimte["_links"]["bijbehorendeWoonplaats"]["href"]
        )
        adressen.append(
            {
                "huisnummer": _hoofdadres["huisnummer"],
                "postcode": _hoofdadres.get("postcode", ""),
                "or_naam": _openbare_ruimte["naam"],
                "woonplaats": _woonplaats["naam"],
            }
        )

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
