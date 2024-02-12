from copy import deepcopy

import factory

from ..constants import KownslTypes

ZAKEN_ROOT = "https://zaken.nl/"
DOCUMENTS_ROOT = "https://drc.nl/"
CATALOGI_ROOT = "http://ztc.nl/"
OBJECTTYPES_ROOT = "http://objecttype.nl/api/v1/"
OBJECTS_ROOT = "http://object.nl/api/v2/"

DOCUMENT_URL = f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/30e4deca-29ca-4798-bab1-3ad75cf29c30"
ZAAK_URL = f"{ZAKEN_ROOT}zaken/0c79c41d-72ef-4ea2-8c4c-03c9945da2a2"

ZAAK_DOCUMENT = {
    "bronorganisatie": "002220647",
    "identificatie": "0000027735",
    "downloadUrl": "",
    "name": "raadsvoorstel.docx",
    "extra": "(Zaakvertrouwelijk)",
    "title": "v2",
}


class UserAssigneeFactory(factory.DictFactory):
    username = "some-author"
    first_name = "Some First"
    last_name = "Some Last"
    full_name = "Some First Some Last"

    class Meta:
        rename = {
            "first_name": "firstName",
            "last_name": "lastName",
            "full_name": "fullName",
        }


class AssignedUsersFactory(factory.DictFactory):
    deadline = "2022-04-14"
    user_assignees = factory.List([factory.SubFactory(UserAssigneeFactory)])
    group_assignees = factory.List([])
    email_notification = False

    class Meta:
        rename = {
            "user_assignees": "userAssignees",
            "email_notification": "emailNotification",
        }


class MetaDataFactory(factory.DictFactory):
    task_definition_id = "submitAdvice"
    process_instance_id = "6ebf534a-bc0a-11ec-a591-c69dd6a420a0"

    class Meta:
        rename = {
            "task_definition_id": "taskDefinitionId",
            "process_instance_id": "processInstanceId",
        }


RR_ID = "14aec7a0-06de-4b55-b839-a1c9a0415b46"


class ReviewRequestFactory(factory.DictFactory):
    assigned_users = factory.List([factory.SubFactory(AssignedUsersFactory)])
    created = "2022-04-14T15:49:09.830235Z"
    documents = factory.List([])
    id = deepcopy(RR_ID)
    is_being_reconfigured = False
    locked = False
    lockReason = ""
    metadata = factory.SubFactory(MetaDataFactory)
    num_reviews_given_before_change = 0
    requester = factory.SubFactory(UserAssigneeFactory)
    review_type = KownslTypes.advice
    toelichting = "some-toelichting"
    user_deadlines = factory.Dict(
        {
            "user:some-author": "2022-04-14",
            "user:some-other-author": "2022-04-15",
        }
    )
    zaak = deepcopy(ZAAK_URL)
    zaakeigenschappen = factory.List([])

    class Meta:
        rename = {
            "assigned_users": "assignedUsers",
            "is_being_reconfigured": "isBeingReconfigured",
            "num_reviews_given_before_change": "numReviewsGivenBeforeChange",
            "review_type": "reviewType",
            "user_deadlines": "userDeadlines",
        }


class AdviceDocumentFactory(factory.DictFactory):
    document = deepcopy(DOCUMENT_URL)
    source_version = 1
    advice_version = 2

    class Meta:
        rename = {"source_version": "sourceVersion", "advice_version": "adviceVersion"}


class AdviceFactory(factory.DictFactory):
    created = "2022-04-14T15:50:09.830235Z"
    author = factory.SubFactory(UserAssigneeFactory)
    advice = "some-advice"
    advice_documents = factory.List([factory.SubFactory(AdviceDocumentFactory)])

    class Meta:
        rename = {
            "advice_documents": "adviceDocuments",
        }


class ApprovalFactory(factory.DictFactory):
    created = ("2022-04-14T15:51:09.830235Z",)
    author = factory.SubFactory(UserAssigneeFactory)
    approved = True
    toelichting = "some-toelichting"


class ReviewsAdviceFactory(factory.DictFactory):
    id = "6a9a169e-aa6f-4dd7-bbea-6bedea74c456"
    reviews = factory.List([factory.SubFactory(AdviceFactory)])
    review_request = deepcopy(RR_ID)
    review_type = KownslTypes.advice
    zaak = deepcopy(ZAAK_URL)

    class Meta:
        rename = {
            "review_request": "reviewRequest",
            "review_type": "reviewType",
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
        "data": ReviewRequestFactory(),
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
        "data": {},
        "geometry": "None",
        "startAt": "1999-12-31",
        "endAt": "None",
        "registrationAt": "1999-12-31",
        "correctionFor": "None",
        "correctedBy": "None",
    },
}
