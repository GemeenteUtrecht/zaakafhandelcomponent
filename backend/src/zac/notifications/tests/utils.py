import os

from requests_mock import Mocker
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.test import generate_oas_component

MOCK_FILES_DIR = os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    "files",
)


def mock_service_oas_get(m: Mocker, url: str, service: str) -> None:
    file_name = f"{service}.yaml"
    file = os.path.join(MOCK_FILES_DIR, file_name)
    oas_url = f"{url}schema/openapi.yaml?v=3"

    with open(file, "rb") as api_spec:
        m.get(oas_url, content=api_spec.read())


ZAKEN_ROOT = "https://some.zrc.nl/api/v1/"
CATALOGI_ROOT = "https://some.ztc.nl/api/v1/"
ZAAK = f"{ZAKEN_ROOT}zaken/f3ff2713-2f53-42ff-a154-16842309ad60"
ZAAKTYPE = f"{CATALOGI_ROOT}zaaktypen/ad4573d0-4d99-4e90-a05c-e08911e8673d"
CATALOGUS = f"{CATALOGI_ROOT}catalogussen/2bd772a5-f1a4-458b-8c13-d2f85c2bfa89"
STATUS = f"{ZAKEN_ROOT}statussen/dd4573d0-4d99-4e90-a05c-e08911e8673e"
STATUSTYPE = f"{CATALOGI_ROOT}statustypen/c612f300-8e16-4811-84f4-78c99fdebe74"
IDENTIFICATIE = "ZAAK-123"
BRONORGANISATIE = "123456782"


ZAAK_RESPONSE = generate_oas_component(
    "zrc",
    "schemas/Zaak",
    url=ZAAK,
    zaaktype=ZAAKTYPE,
    identificatie=IDENTIFICATIE,
    bronorganisatie=BRONORGANISATIE,
    resultaat=f"{ZAKEN_ROOT}resultaten/f3ff2713-2f53-42ff-a154-16842309ad60",
    registratiedatum="2020-04-15",
    startdatum="2020-04-15",
    einddatum=None,
    uiterlijke_einddatum_afdoening=None,
    publicatiedatum=None,
    vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.geheim,
    status=None,
    zaakgeometrie=None,
    relevante_andere_zaken=[],
)


ZAAKTYPE_RESPONSE = generate_oas_component(
    "ztc",
    "schemas/ZaakType",
    url=ZAAKTYPE,
    identificatie="zt",
    omschrijving="some zaaktype",
    catalogus=CATALOGUS,
)

STATUSTYPE_RESPONSE = generate_oas_component(
    "ztc",
    "schemas/StatusType",
    url=STATUSTYPE,
)

STATUS_RESPONSE = generate_oas_component(
    "zrc",
    "schemas/Status",
    url=STATUS,
    statustype=STATUSTYPE,
    statustoelichting="some-statustoelichting",
)
