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


CHECKLISTTYPE_OBJECTTYPE = {
    "url": f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646eae/versions/4",
    "version": 4,
    "objectType": f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646eae",
    "status": "published",
    "jsonSchema": {
        "type": "object",
        "title": "ChecklistType",
        "required": [
            "zaaktypeCatalogus",
            "zaaktypeIdentificaties",
            "questions",
        ],
        "properties": {
            "questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "title": "ChecklistQuestion",
                    "required": ["question", "choices", "order"],
                    "properties": {
                        "order": {"type": "integer"},
                        "choices": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "naam": {"type": "string"},
                                    "waarde": {"type": "string"},
                                },
                            },
                        },
                        "question": {"type": "string"},
                    },
                },
            },
            "zaaktypeCatalogus": {"type": "string"},
            "zaaktypeIdentificaties": {"type": "array", "items": {"type": "string"}},
        },
    },
    "createdAt": "1999-12-31",
    "modifiedAt": "1999-12-31",
    "publishedAt": "1999-12-31",
}

CHECKLISTTYPE_OBJECT = {
    "url": f"{OBJECTS_ROOT}objects/85e6c250-9f51-4286-8340-25109d0b96d1",
    "uuid": "85e6c250-9f51-4286-8340-25109d0b96d1",
    "type": f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646eae",
    "record": {
        "index": 1,
        "typeVersion": 4,
        "data": {
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
        },
        "geometry": "None",
        "startAt": "1999-12-31",
        "endAt": "None",
        "registrationAt": "1999-12-31",
        "correctionFor": "None",
        "correctedBy": "None",
    },
}

CHECKLIST_OBJECTTYPE = {
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
CHECKLIST_OBJECTTYPE_LATEST_VERSION = {
    "url": f"{OBJECTTYPES_ROOT}objecttypes/5d7182f4-dc2f-4aaa-b2a2-bdc72a2ce0b4/versions/3",
    "version": 3,
    "objectType": f"{OBJECTTYPES_ROOT}objecttypes/5d7182f4-dc2f-4aaa-b2a2-bdc72a2ce0b4",
    "status": "published",
    "jsonSchema": {
        "type": "object",
        "$defs": {
            "user": {
                "type": ["null", "object"],
                "title": "user",
                "required": [
                    "username",
                    "firstName",
                    "fullName",
                    "lastName",
                    "email",
                ],
                "properties": {
                    "email": {"type": "string"},
                    "fullName": {"type": "string"},
                    "lastName": {"type": "string"},
                    "username": {"type": "string"},
                    "firstName": {"type": "string"},
                },
            },
            "group": {
                "type": ["null", "object"],
                "title": "group",
                "required": ["name", "fullName"],
                "properties": {
                    "name": {"type": "string"},
                    "fullName": {"type": "string"},
                },
            },
            "answer": {
                "type": "object",
                "title": "ChecklistAnswer",
                "required": ["question", "answer", "created"],
                "properties": {
                    "answer": {"type": "string"},
                    "remarks": {"type": "string"},
                    "document": {"type": "string"},
                    "question": {"type": "string"},
                    "userAssignee": {"$ref": "#/$defs/user"},
                    "groupAssignee": {"$ref": "#/$defs/group"},
                    "created": {"type": "string"},
                },
            },
        },
        "title": "Checklist",
        "required": ["answers", "zaak", "locked"],
        "properties": {
            "zaak": {"type": "string"},
            "answers": {
                "type": "array",
                "items": {"$ref": "#/$defs/answer"},
            },
            "locked": {"type": "boolean", "value": False},
        },
    },
    "createdAt": "1999-12-31",
    "modifiedAt": "1999-12-31",
    "publishedAt": "1999-12-31",
}

CHECKLIST_OBJECT = {
    "url": f"{OBJECTS_ROOT}objects/85e6c250-9f51-4286-8340-25109d0b96d1",
    "uuid": "85e6c250-9f51-4286-8340-25109d0b96d1",
    "type": f"{OBJECTTYPES_ROOT}objecttypes/5d7182f4-dc2f-4aaa-b2a2-bdc72a2ce0b4",
    "record": {
        "index": 1,
        "typeVersion": 3,
        "data": {
            "zaak": ZAAK_URL,
            "answers": [
                {
                    "answer": "Ja",
                    "question": "Ja?",
                    "groupAssignee": None,
                    "userAssignee": None,
                    "created": "1999-12-31T23:59:59+00:00",
                    "document": "",
                    "remarks": "",
                },
                {
                    "answer": "",
                    "question": "Nee?",
                    "groupAssignee": None,
                    "userAssignee": None,
                    "created": "1999-12-31T23:59:59+00:00",
                    "document": "",
                    "remarks": "",
                },
            ],
            "locked": False,
        },
        "geometry": "None",
        "startAt": "1999-12-31",
        "endAt": "None",
        "registrationAt": "1999-12-31",
        "correctionFor": "None",
        "correctedBy": "None",
    },
}
