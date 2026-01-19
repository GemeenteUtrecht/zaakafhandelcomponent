import yaml

from zac.contrib.objects.tests.utils import OBJECTS_ROOT, OBJECTTYPES_ROOT
from zac.tests.compat import generate_oas_component, read_schema
from zac.tests.utils import update_dictionary_from_kwargs

ZAKEN_ROOT = "https://open-zaak.nl/zaken/api/v1/"
CATALOGI_ROOT = "https://open-zaak.nl/catalogi/api/v1/"
BRONORGANISATIE = "123456789"
IDENTIFICATIE = "ZAAK-0000001"
OBJECTTYPES_ROOT = "http://objecttype.nl/api/v2/"
OBJECTS_ROOT = "http://object.nl/api/v2/"
ZAAK_URL = f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7"


def OudbehandelarenObjectTypeFactory(**kwargs):
    default_data = {
        "url": f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646eae/versions/4",
        "version": 4,
        "objectType": f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646eae",
        "status": "published",
        "jsonSchema": yaml.safe_load(read_schema("metaobjecttypes"))["components"][
            "schemas"
        ]["Oudbehandelaar"],
        "createdAt": "1999-12-31",
        "modifiedAt": "1999-12-31",
        "publishedAt": "1999-12-31",
    }
    if kwargs:
        update_dictionary_from_kwargs(default_data, kwargs)

    return generate_oas_component(
        "objecttypes", "schemas/ObjectVersion", **default_data
    )


def OudbehandelarenObjectFactory(**kwargs):
    default_data = {
        "url": f"{OBJECTS_ROOT}objects/85e6c250-9f51-4286-8340-25109d0b96d1",
        "uuid": "85e6c250-9f51-4286-8340-25109d0b96d1",
        "type": f"{OBJECTTYPES_ROOT}objecttypes/5d7182f4-dc2f-4aaa-b2a2-bdc72a2ce0b4",
        "record": {
            "index": 1,
            "typeVersion": 3,
            "data": {
                "zaak": ZAAK_URL,
                "oudbehandelaren": [
                    {
                        "email": "some-email@email.com",
                        "ended": "2023-01-01",
                        "started": "2023-01-02",
                        "identificatie": "some-username",
                        "changedBy": "user:some-username",
                    }
                ],
            },
            "geometry": "None",
            "startAt": "1999-12-31",
            "endAt": "None",
            "registrationAt": "1999-12-31",
            "correctionFor": "None",
            "correctedBy": "None",
        },
    }
    if kwargs:
        update_dictionary_from_kwargs(default_data, kwargs)

    return generate_oas_component("objects", "schemas/Object", **default_data)
