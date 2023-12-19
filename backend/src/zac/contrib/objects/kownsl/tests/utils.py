from ..constants import KownslTypes

ZAKEN_ROOT = "https://zaken.nl/"
DOCUMENTS_ROOT = "https://drc.nl/"
CATALOGI_ROOT = "http://ztc.nl/"
OBJECTTYPES_ROOT = "http://objecttype.nl/api/v1/"
OBJECTS_ROOT = "http://object.nl/api/v2/"

DOCUMENT_URL = f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/30e4deca-29ca-4798-bab1-3ad75cf29c30"
ZAAK_URL = f"{ZAKEN_ROOT}api/zaken/0c79c41d-72ef-4ea2-8c4c-03c9945da2a2"

ZAAK_DOCUMENT = {
    "bronorganisatie": "002220647",
    "identificatie": "0000027735",
    "downloadUrl": "",
    "name": "raadsvoorstel.docx",
    "extra": "(Zaakvertrouwelijk)",
    "title": "v2",
}

REVIEW_REQUEST = {
    "assignedUsers": [
        {
            "deadline": "2022-04-14",
            "userAssignees": [
                {
                    "username": "some-author",
                    "firstName": "Some First",
                    "lastName": "Some Last",
                    "fullName": "Some First Some Last",
                }
            ],
            "groupAssignees": [],
            "emailNotification": False,
        },
        {
            "deadline": "2022-04-15",
            "userAssignees": [
                {
                    "username": "some-other-author",
                    "firstName": "Some Other First",
                    "lastName": "Some Last",
                    "fullName": "Some Other First Some Last",
                }
            ],
            "groupAssignees": [],
            "emailNotification": False,
        },
    ],
    "created": "2022-04-14T15:49:09.830235Z",
    "documents": list(),
    "id": "14aec7a0-06de-4b55-b839-a1c9a0415b46",
    "isBeingReconfigured": False,
    "locked": False,
    "lockReason": "",
    "metadata": {
        "taskDefinitionId": "submitAdvice",
        "processInstanceId": "6ebf534a-bc0a-11ec-a591-c69dd6a420a0",
    },
    "numReviewsGivenBeforeChange": 0,
    "requester": {
        "username": "some-author",
        "firstName": "Some First",
        "lastName": "Some Last",
        "fullName": "Some First Some Last",
    },
    "reviewType": KownslTypes.advice,
    "toelichting": "some-toelichting",
    "userDeadlines": {
        "user:some-author": "2022-04-14",
        "user:some-other-author": "2022-04-15",
    },
    "zaak": ZAAK_URL,
}

ADVICE = {
    "created": "2022-04-14T15:50:09.830235Z",
    "author": {
        "username": "some-author",
        "firstName": "Some First",
        "lastName": "Some Last",
        "fullName": "Some First Some Last",
    },
    "advice": "some-advice",
    "adviceDocuments": [
        {"document": DOCUMENT_URL, "sourceVersion": 1, "adviceVersion": 2}
    ],
}

APPROVAL = {
    "created": "2022-04-14T15:51:09.830235Z",
    "author": {
        "username": "some-author",
        "firstName": "Some First",
        "lastName": "Some Last",
        "fullName": "Some First Some Last",
    },
    "approved": True,
    "toelichting": "some-toelichting",
}


REVIEWS_ADVICE = {
    "id": "6a9a169e-aa6f-4dd7-bbea-6bedea74c456",
    "meta": True,
    "reviews": [ADVICE],
    "reviewRequest": REVIEW_REQUEST["id"],
    "reviewType": "advice",
    "zaak": ZAAK_URL,
}

REVIEW_REQUEST_OBJECTTYPE = {
    "url": f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646eae",
    "uuid": "b4ec3f47-bc20-4872-955c-cb5f67646eae",
    "name": "ReviewRequest",
    "namePlural": "ReviewRequests",
    "description": "Describes the json schema of a review request.",
    "dataClassification": "open",
    "maintainerOrganization": "",
    "maintainerDepartment": "",
    "contactPerson": "",
    "contactEmail": "",
    "source": "",
    "updateFrequency": "unknown",
    "providerOrganization": "",
    "documentationUrl": "",
    "labels": dict(),
    "createdAt": "1999-12-31",
    "modifiedAt": "1999-12-31",
    "versions": [
        f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646eae/versions/4",
        f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646eae/versions/3",
        f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646eae/versions/2",
        f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646eae/versions/1",
    ],
}


REVIEW_REQUEST_OBJECTTYPE_LATEST_VERSION = {
    "url": f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646eae/versions/4",
    "version": 4,
    "objectType": f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646eae",
    "status": "published",
    "jsonSchema": {
        "type": "object",
        "$defs": {
            "user": {
                "type": "object",
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
                "type": "object",
                "title": "group",
                "required": ["name", "fullName"],
                "properties": {
                    "name": {"type": "string"},
                    "fullName": {"type": "string"},
                },
            },
            "assignedUser": {
                "type": "object",
                "title": "AssignedUser",
                "required": [
                    "deadline",
                    "emailNotification",
                    "userAssignees",
                    "groupAssignees",
                ],
                "properties": {
                    "deadline": {"type": "string"},
                    "userAssignees": {
                        "type": "array",
                        "items": {"$ref": "#/$defs/user"},
                    },
                    "groupAssignees": {
                        "type": "array",
                        "items": {"$ref": "#/$defs/group"},
                    },
                    "emailNotification": {"type": "boolean"},
                },
            },
        },
        "title": "ReviewRequest",
        "required": [
            "assignedUsers",
            "created",
            "documents",
            "id",
            "isBeingReconfigured",
            "locked",
            "lockReason",
            "meta",
            "metadata",
            "numReviewsGivenBeforeChange",
            "requester",
            "reviewType",
            "toelichting",
            "userDeadlines",
            "zaak",
        ],
        "properties": {
            "id": {"type": "string"},
            "meta": True,
            "zaak": {"type": "string"},
            "locked": {"type": "boolean"},
            "created": {"type": "string"},
            "metadata": {
                "type": "object",
                "title": "Metadata",
                "properties": {
                    "taskDefinitionId": {"type": "string"},
                    "processInstanceId": {"type": "string"},
                },
            },
            "documents": {"type": "array", "items": {"type": "string"}},
            "requester": {"$ref": "#/$defs/user"},
            "lockReason": {"type": "string"},
            "reviewType": {"type": "string"},
            "toelichting": {"type": "string"},
            "assignedUsers": {
                "type": "array",
                "items": {"$ref": "#/$defs/assignedUser"},
            },
            "userDeadlines": {"type": "object"},
            "isBeingReconfigured": {"type": "boolean"},
            "numReviewsGivenBeforeChange": {"type": "integer"},
        },
    },
    "createdAt": "1999-12-31",
    "modifiedAt": "1999-12-31",
    "publishedAt": "1999-12-31",
}

REVIEW_REQUEST_OBJECT = {
    "url": f"{OBJECTS_ROOT}objects/85e6c250-9f51-4286-8340-25109d0b96d1",
    "uuid": "85e6c250-9f51-4286-8340-25109d0b96d1",
    "type": f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646ead",
    "record": {
        "index": 1,
        "typeVersion": 4,
        "data": REVIEW_REQUEST,
        "geometry": "None",
        "startAt": "1999-12-31",
        "endAt": "None",
        "registrationAt": "1999-12-31",
        "correctionFor": "None",
        "correctedBy": "None",
    },
}

REVIEW_OBJECTTYPE = {
    "url": f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646ead",
    "uuid": "b4ec3f47-bc20-4872-955c-cb5f67646ead",
    "name": "Review",
    "namePlural": "Reviews",
    "description": "Describes the json schema of a review.",
    "dataClassification": "open",
    "maintainerOrganization": "",
    "maintainerDepartment": "",
    "contactPerson": "",
    "contactEmail": "",
    "source": "",
    "updateFrequency": "unknown",
    "providerOrganization": "",
    "documentationUrl": "",
    "labels": dict(),
    "createdAt": "1999-12-31",
    "modifiedAt": "1999-12-31",
    "versions": [
        f"{OBJECTTYPES_ROOT}objecttypes/b3ec3f47-bc20-4872-955c-cb5f67646ead/versions/4",
        f"{OBJECTTYPES_ROOT}objecttypes/b3ec3f47-bc20-4872-955c-cb5f67646ead/versions/3",
        f"{OBJECTTYPES_ROOT}objecttypes/b3ec3f47-bc20-4872-955c-cb5f67646ead/versions/2",
        f"{OBJECTTYPES_ROOT}objecttypes/b3ec3f47-bc20-4872-955c-cb5f67646ead/versions/1",
    ],
}


REVIEW_OBJECTTYPE_LATEST_VERSION = {
    "url": f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646ead/versions/4",
    "version": 4,
    "objectType": f"{OBJECTTYPES_ROOT}objecttypes/b3ec3f47-bc20-4872-955c-cb5f67646ead",
    "status": "published",
    "jsonSchema": {
        "type": "object",
        "$defs": {
            "id": {"type": "string"},
            "user": {
                "type": "object",
                "title": "user",
                "required": ["username", "firstName", "fullName", "lastName", "email"],
                "properties": {
                    "email": {"type": "string"},
                    "fullName": {"type": "string"},
                    "lastName": {"type": "string"},
                    "username": {"type": "string"},
                    "firstName": {"type": "string"},
                },
            },
            "zaak": {"type": "string"},
            "group": {
                "type": "object",
                "title": "group",
                "required": ["name", "fullName"],
                "properties": {
                    "name": {"type": "string"},
                    "fullName": {"type": "string"},
                },
            },
            "advice": {
                "type": "object",
                "title": "Advice",
                "required": ["advice", "author", "created"],
                "properties": {
                    "group": {"$ref": "#/$defs/group"},
                    "advice": {"type": "string"},
                    "author": {"$ref": "#/$defs/user"},
                    "created": {"$ref": "#/$defs/created"},
                    "adviceDocuments": {
                        "type": "array",
                        "items": {"$ref": "#/$defs/adviceDocument"},
                    },
                },
            },
            "created": {"type": "string"},
            "approval": {
                "name": "Approval",
                "type": "object",
                "required": ["approved", "author", "created", "toelichting"],
                "properties": {
                    "group": {"$ref": "#/$defs/group"},
                    "author": {"$ref": "#/$defs/user"},
                    "created": {"$ref": "#/$defs/created"},
                    "approved": {"type": "boolean"},
                    "toelichting": {"type": "string"},
                },
            },
            "reviewType": {"type": "string"},
            "reviewRequest": {"type": "string"},
            "adviceDocument": {
                "type": "object",
                "title": "AdviceDocument",
                "required": ["url", "sourceVersion", "adviceVersion"],
                "properties": {
                    "url": {"type": "string"},
                    "adviceVersion": {"type": "string"},
                    "sourceVersion": {"type": "string"},
                },
            },
        },
        "title": "Reviews",
        "required": ["id", "meta", "reviewRequest", "reviewType", "zaak", "reviews"],
        "properties": {
            "id": {"$ref": "#/$defs/id"},
            "meta": True,
            "zaak": {"$ref": "#/$defs/zaak"},
            "reviews": {
                "type": "array",
                "items": {
                    "oneOf": [{"$ref": "#/$defs/advice"}, {"$ref": "#/$defs/approval"}]
                },
            },
            "reviewType": {"$ref": "#/$defs/reviewType"},
            "reviewRequest": {"$ref": "#/$defs/reviewRequest"},
        },
    },
    "createdAt": "1999-12-31",
    "modifiedAt": "1999-12-31",
    "publishedAt": "1999-12-31",
}

REVIEW_OBJECT = {
    "url": f"{OBJECTS_ROOT}objects/85e6c250-9f51-4286-8340-25109d0b96d1",
    "uuid": "85e6c250-9f51-4286-8340-25109d0b96d1",
    "type": f"{OBJECTTYPES_ROOT}objecttypes/b3ec3f47-bc20-4872-955c-cb5f67646ead",
    "record": {
        "index": 1,
        "typeVersion": 4,
        "data": REVIEWS_ADVICE,
        "geometry": "None",
        "startAt": "1999-12-31",
        "endAt": "None",
        "registrationAt": "1999-12-31",
        "correctionFor": "None",
        "correctedBy": "None",
    },
}
