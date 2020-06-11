from typing import Any, Dict

from zgw_consumers.client import ZGWClient

from .models import KownslConfig


def get_client() -> ZGWClient:
    config = KownslConfig.get_solo()
    assert config.service, "A service must be configured first"
    return config.service.build_client()


def create_review_request(zaak_url: str, review_type: str = "advice") -> Dict[str, Any]:
    client = get_client()
    data = {
        "for_zaak": zaak_url,
        "review_type": review_type,
    }
    resp = client.create("reviewrequest", data=data)
    return resp
