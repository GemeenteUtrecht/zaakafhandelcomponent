from zgw_consumers.api_models.zaken import Zaak

from zac.core.services import _client_from_url


def get_service_variables(self, zaak: Zaak) -> dict:
    # Build service variables to continue execution
    zrc_client = _client_from_url(zaak.url)
    ztc_client = _client_from_url(zaak.zaaktype)

    zrc_jwt = zrc_client.auth.credentials()["Authorization"]
    ztc_jwt = ztc_client.auth.credentials()["Authorization"]

    return {
        "services": {
            "zrc": {"jwt": zrc_jwt},
            "ztc": {"jwt": ztc_jwt},
        },
    }
