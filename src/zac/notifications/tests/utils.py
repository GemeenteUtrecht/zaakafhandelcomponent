import os

from requests_mock import Mocker

MOCK_FILES_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "files",)


def mock_service_oas_get(m: Mocker, url: str, service: str) -> None:
    file_name = f"{service}.yaml"
    file = os.path.join(MOCK_FILES_DIR, file_name)
    oas_url = f"{url}schema/openapi.yaml?v=3"

    with open(file, "rb") as api_spec:
        m.get(oas_url, content=api_spec.read())


ZAAK = "https://some.zrc.nl/api/v1/zaken/f3ff2713-2f53-42ff-a154-16842309ad60"
ZAAKTYPE = "https://some.ztc.nl/api/v1/zaaktypen/ad4573d0-4d99-4e90-a05c-e08911e8673d"

IDENTIFICATIE = "ZAAK-123"
BRONORGANISATIE = "123456782"

ZAAK_RESPONSE = {
    "url": ZAAK,
    "identificatie": IDENTIFICATIE,
    "bronorganisatie": BRONORGANISATIE,
    "zaaktype": ZAAKTYPE,
    "resultaat": "https://some.zrc.nl/api/v1/resultaten/f3ff2713-2f53-42ff-a154-16842309ad60",
    "omschrijving": "",
    "toelichting": "",
    "registratiedatum": "2020-04-15",
    "startdatum": "2020-04-15",
    "einddatum": None,
    "einddatum_gepland": None,
    "uiterlijke_einddatum_afdoening": None,
    "publicatiedatum": None,
    "vertrouwelijkheidaanduiding": "geheim",
    "status": None,
    "relevante_andere_zaken": [],
    "zaakgeometrie": None,
}
