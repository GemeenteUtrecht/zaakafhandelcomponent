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
OBJECTS_ROOT = "https://some.objects.nl/api/v1/"
OBJECTTYPES_ROOT = "https://some.objecttypes.nl/api/v2/"
DRC_ROOT = "https://some.drc.nl/api/v1/"
ZAAK = f"{ZAKEN_ROOT}zaken/f3ff2713-2f53-42ff-a154-16842309ad60"
ZAAKTYPE = f"{CATALOGI_ROOT}zaaktypen/ad4573d0-4d99-4e90-a05c-e08911e8673d"
CATALOGUS = f"{CATALOGI_ROOT}catalogussen/2bd772a5-f1a4-458b-8c13-d2f85c2bfa89"
STATUS = f"{ZAKEN_ROOT}statussen/dd4573d0-4d99-4e90-a05c-e08911e8673e"
STATUSTYPE = f"{CATALOGI_ROOT}statustypen/c612f300-8e16-4811-84f4-78c99fdebe74"
INFORMATIEOBJECT = (
    f"{DRC_ROOT}enkelvoudiginformatieobjecten/d34d134f-a7a4-40a6-82fd-4d94b8e375db"
)
INFORMATIEOBJECTTYPE = (
    f"{CATALOGI_ROOT}informatieobjecttypen/8db7fbe6-e4a0-45d4-9403-1928519fe28d"
)
ZAAKINFORMATIEOBJECT = (
    f"{ZAKEN_ROOT}zaakinformatieobjecten/71a42e62-7ed0-446a-b03a-bc9beaf58f85"
)
OBJECT = f"{OBJECTS_ROOT}objects/f8a7573a-758f-4a19-aa22-245bb8f4712e"
ZAAKOBJECT = f"{ZAKEN_ROOT}zaakobjecten/69e98129-1f0d-497f-bbfb-84b88137edbc"
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

CATALOGUS_RESPONSE = generate_oas_component(
    "ztc", "schemas/Catalogus", url=CATALOGUS, domein="DOME"
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
    "ztc", "schemas/StatusType", url=STATUSTYPE, isEindstatus=False
)

STATUS_RESPONSE = generate_oas_component(
    "zrc",
    "schemas/Status",
    url=STATUS,
    statustype=STATUSTYPE,
    statustoelichting="some-statustoelichting",
)

ZAAKINFORMATIEOBJECT_RESPONSE = generate_oas_component(
    "zrc",
    "schemas/ZaakInformatieObject",
    url=ZAAKINFORMATIEOBJECT,
    informatieobject=INFORMATIEOBJECT,
    zaak=ZAAK,
    titel="SOMETITEL",
)

ZAAKOBJECT_RESPONSE = generate_oas_component(
    "zrc",
    "schemas/ZaakObject",
    url=ZAAKOBJECT,
    object=OBJECT,
    zaak=ZAAK,
    object_identificatie=None,
)

INFORMATIEOBJECT_RESPONSE = generate_oas_component(
    "drc",
    "schemas/EnkelvoudigInformatieObject",
    url=INFORMATIEOBJECT,
    informatieobjecttype=INFORMATIEOBJECTTYPE,
    titel="SOMETITEL",
)

INFORMATIEOBJECTTYPE_RESPONSE = generate_oas_component(
    "ztc",
    "schemas/InformatieObjectType",
    url=INFORMATIEOBJECTTYPE,
)

OBJECTTYPE_RESPONSE = {
    "url": f"{OBJECTTYPES_ROOT}objecttypes/1ddc6ea4-6d7f-4573-8f2d-6473eb1ceb5e",
    "uuid": "1ddc6ea4-6d7f-4573-8f2d-6473eb1ceb5e",
    "name": "Pand Utrecht NG",
    "namePlural": "Panden Utrecht NG",
    "description": "",
    "dataClassification": "open",
    "maintainerOrganization": "",
    "maintainerDepartment": "",
    "contactPerson": "",
    "contactEmail": "",
    "source": "",
    "updateFrequency": "unknown",
    "providerOrganization": "",
    "documentationUrl": "",
    "labels": {"stringRepresentation": ["field__VELD"]},
    "createdAt": "2023-01-02",
    "modifiedAt": "2023-01-02",
    "versions": [
        f"{OBJECTTYPES_ROOT}objecttypes/1ddc6ea4-6d7f-4573-8f2d-6473eb1ceb5e/versions/1"
    ],
}

OBJECTTYPE_VERSION_RESPONSE = {
    "url": f"{OBJECTTYPES_ROOT}objecttypes/1ddc6ea4-6d7f-4573-8f2d-6473eb1ceb5e/versions/1",
    "version": 1,
    "objectType": f"{OBJECTTYPES_ROOT}objecttypes/1ddc6ea4-6d7f-4573-8f2d-6473eb1ceb5e",
    "status": "published",
    "jsonSchema": {
        "$id": "https://example.com/example.json",
        "type": "object",
        "title": "Pand Utrecht",
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "default": {},
        "examples": [{"VELD": "1234"}],
        "required": ["VELD"],
        "properties": {
            "VELD": {"type": "integer", "description": "integer veld"},
        },
        "description": "Een pand van de gemeente Utrecht.",
    },
    "createdAt": "2023-01-02",
    "modifiedAt": "2023-01-02",
    "publishedAt": "2023-01-02",
}


OBJECT_RESPONSE = {
    "url": OBJECT,
    "uuid": "f8a7573a-758f-4a19-aa22-245bb8f4712e",
    "type": OBJECTTYPE_RESPONSE["url"],
    "record": {
        "index": 1,
        "typeVersion": 1,
        "data": {
            "VELD": "1234",
        },
        "geometry": {
            "type": "Point",
            "coordinates": [5.133365001529453, 52.07746853707585],
        },
        "startAt": "2022-12-15",
        "endAt": None,
        "registrationAt": "2022-12-15",
        "correctionFor": None,
        "correctedBy": None,
    },
    "stringRepresentation": "1234",
}
