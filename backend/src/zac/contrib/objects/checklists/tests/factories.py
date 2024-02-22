import yaml
from zgw_consumers.test import generate_oas_component, read_schema

from zac.contrib.objects.tests.utils import OBJECTS_ROOT, OBJECTTYPES_ROOT
from zac.tests.utils import update_dictionary_from_kwargs

import factory

from zac.accounts.tests.factories import UserFactory
from zac.contrib.objects.tests.utils import OBJECTS_ROOT, OBJECTTYPES_ROOT


class ChecklistLockFactory(factory.django.DjangoModelFactory):
    url = factory.Faker("url")
    user = factory.SubFactory(UserFactory)
    zaak = factory.Faker("url")
    zaak_identificatie = factory.Faker("word")

    class Meta:
        model = "checklists.ChecklistLock"
        django_get_or_create = (
            "url",
            "zaak",
        )

ZAKEN_ROOT = "https://open-zaak.nl/zaken/api/v1/"
CATALOGI_ROOT = "https://open-zaak.nl/catalogi/api/v1/"
BRONORGANISATIE = "123456789"
IDENTIFICATIE = "ZAAK-0000001"
ZAAK_URL = f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7"


def ChecklistTypeObjectTypeVersionFactory(**kwargs):
    default_data = {
        "url": f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646eae/versions/4",
        "version": 4,
        "objectType": f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646eae",
        "status": "published",
        "jsonSchema": yaml.safe_load(read_schema("metaobjecttypes"))["components"][
            "schemas"
        ]["ChecklistType"],
        "createdAt": "1999-12-31",
        "modifiedAt": "1999-12-31",
        "publishedAt": "1999-12-31",
    }
    if kwargs:
        update_dictionary_from_kwargs(default_data, kwargs)

    return generate_oas_component(
        "objecttypes", "schemas/ObjectVersion", **default_data
    )


def ChecklistTypeFactory(**kwargs):
    default_data = {
        "zaaktypeCatalogus": "UTRE",
        "zaaktypeIdentificaties": ["ZT1"],
        "questions": [
            {
                "choices": [{"name": "Ja", "value": "Ja"}],
                "question": "Ja?",
                "order": 1,
            },
            {
                "choices": [{"name": "Nee", "value": "Nee"}],
                "question": "Nee?",
                "order": 2,
            },
        ],
    }
    if kwargs:
        update_dictionary_from_kwargs(default_data, kwargs)

    return generate_oas_component(
        "metaobjecttypes", "schemas/ChecklistType", **default_data
    )


def ChecklistTypeObjectFactory(**kwargs):
    default_data = {
        "url": f"{OBJECTS_ROOT}objects/85e6c250-9f51-4286-8340-25109d0b96d1",
        "uuid": "85e6c250-9f51-4286-8340-25109d0b96d1",
        "type": f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646eae",
        "record": {
            "index": 1,
            "typeVersion": 4,
            "data": ChecklistTypeFactory(),
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

    return generate_oas_component(
        "objects",
        "schemas/Object",
        **default_data,
    )


def ChecklistObjectTypeFactory(**kwargs):
    default_data = {
        "url": f"{OBJECTTYPES_ROOT}objecttypes/5d7182f4-dc2f-4aaa-b2a2-bdc72a2ce0b4",
        "uuid": "5d7182f4-dc2f-4aaa-b2a2-bdc72a2ce0b4",
        "name": "Checklist",
        "namePlural": "Checklists",
        "description": "Describes the json schema of a checklist",
        "dataClassification": "open",
        "maintainerOrganization": "",
        "maintainerDepartment": "",
        "contactPerson": "",
        "contactEmail": "",
        "source": "",
        "updateFrequency": "unknown",
        "providerOrganization": "",
        "documentationUrl": "",
        "labels": {},
        "createdAt": "1999-12-31",
        "modifiedAt": "1999-12-31",
        "versions": [
            f"{OBJECTTYPES_ROOT}objecttypes/5d7182f4-dc2f-4aaa-b2a2-bdc72a2ce0b4/versions/3",
            f"{OBJECTTYPES_ROOT}objecttypes/5d7182f4-dc2f-4aaa-b2a2-bdc72a2ce0b4/versions/2",
            f"{OBJECTTYPES_ROOT}objecttypes/5d7182f4-dc2f-4aaa-b2a2-bdc72a2ce0b4/versions/1",
        ],
    }
    if kwargs:
        update_dictionary_from_kwargs(default_data, kwargs)

    return generate_oas_component(
        "objecttypes",
        "schemas/ObjectType",
        **default_data,
    )


def ChecklistObjectTypeVersionFactory(**kwargs):
    default_data = {
        "url": f"{OBJECTTYPES_ROOT}objecttypes/5d7182f4-dc2f-4aaa-b2a2-bdc72a2ce0b4/versions/3",
        "version": 3,
        "objectType": f"{OBJECTTYPES_ROOT}objecttypes/5d7182f4-dc2f-4aaa-b2a2-bdc72a2ce0b4",
        "status": "published",
        "jsonSchema": yaml.safe_load(read_schema("metaobjecttypes"))["components"][
            "schemas"
        ]["Checklist"],
        "createdAt": "1999-12-31",
        "modifiedAt": "1999-12-31",
        "publishedAt": "1999-12-31",
    }
    if kwargs:
        update_dictionary_from_kwargs(default_data, kwargs)

    return generate_oas_component(
        "objecttypes",
        "schemas/ObjectVersion",
        **default_data,
    )


def ChecklistFactory(**kwargs):
    default_data = {
        "zaak": ZAAK_URL,
        "answers": [
            {"answer": "Ja", "question": "Ja?"},
            {"answer": "Nee", "question": "Nee?"},
        ],
        "lockedBy": None,
    }
    if kwargs:
        update_dictionary_from_kwargs(default_data, kwargs)

    return generate_oas_component(
        "metaobjecttypes",
        "schemas/Checklist",
        **default_data,
    )


def ChecklistObjectFactory(**kwargs):
    default_data = {
        "url": f"{OBJECTS_ROOT}objects/85e6c250-9f51-4286-8340-25109d0b96d1",
        "uuid": "85e6c250-9f51-4286-8340-25109d0b96d1",
        "type": f"{OBJECTTYPES_ROOT}objecttypes/5d7182f4-dc2f-4aaa-b2a2-bdc72a2ce0b4",
        "record": {
            "index": 1,
            "typeVersion": 3,
            "data": ChecklistFactory(),
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

    return generate_oas_component(
        "objects",
        "schemas/Object",
        **default_data,
    )
