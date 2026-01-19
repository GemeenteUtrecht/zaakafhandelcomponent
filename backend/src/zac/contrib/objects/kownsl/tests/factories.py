from copy import deepcopy
from typing import Dict, Optional

import factory
import yaml

from zac.contrib.objects.tests.utils import OBJECTS_ROOT, OBJECTTYPES_ROOT
from zac.tests.compat import generate_oas_component, read_schema
from zac.tests.utils import update_dictionary_from_kwargs

from ..constants import KownslTypes

ZAKEN_ROOT = "https://zaken.nl/"
DOCUMENTS_ROOT = "https://drc.nl/"
CATALOGI_ROOT = "http://ztc.nl/"
OBJECTTYPES_ROOT = "http://objecttype.nl/api/v2/"
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

RR_ID = "14aec7a0-06de-4b55-b839-a1c9a0415b46"


def user_assignee_factory(**kwargs):
    default_data = {
        "email": "some-author@email.zac",
        "username": "some-author",
        "firstName": "Some First",
        "lastName": "Some Last",
        "fullName": "Some First Some Last",
    }
    if kwargs:
        update_dictionary_from_kwargs(default_data, kwargs)

    return generate_oas_component(
        "metaobjecttypes",
        "schemas/ReviewRequest/$defs/user",
        **default_data,
    )


def assigned_user_factory(**kwargs):
    default_data = {
        "deadline": "2022-04-14",
        "groupAssignees": [],
        "userAssignees": [user_assignee_factory()],
        "emailNotification": False,
    }
    if kwargs:
        update_dictionary_from_kwargs(default_data, kwargs)

    return generate_oas_component(
        "metaobjecttypes",
        "schemas/ReviewRequest/$defs/assignedUser",
        **default_data,
    )


def meta_data_factory(**kwargs):
    default_data = {
        "taskDefinitionId": "submitAdvice",
        "processInstanceId": "6ebf534a-bc0a-11ec-a591-c69dd6a420a0",
    }
    if kwargs:
        update_dictionary_from_kwargs(default_data, kwargs)

    return generate_oas_component(
        "metaobjecttypes",
        "schemas/ReviewRequest/properties/metadata",
        **default_data,
    )


def review_request_factory(**kwargs):
    assigned_users = [assigned_user_factory()]
    assigned_users.append(
        {
            "deadline": "2022-04-15",
            "groupAssignees": [],
            "userAssignees": [
                user_assignee_factory(
                    email="some-other-author@email.zac",
                    username="some-other-author",
                    firstName="Some Other First",
                    lastName="Some Last",
                    fullName="Some Other First Some Last",
                )
            ],
            "emailNotification": False,
        }
    )
    default_data = {
        "created": "2022-04-14T15:49:09.830235Z",
        "documents": [],
        "id": "14aec7a0-06de-4b55-b839-a1c9a0415b46",
        "locked": False,
        "lockReason": "",
        "metadata": meta_data_factory(),
        "requester": user_assignee_factory(),
        "toelichting": "some-toelichting",
        "zaak": ZAAK_URL,
        "zaakeigenschappen": [],
        "assignedUsers": assigned_users,
        "isBeingReconfigured": False,
        "numReviewsGivenBeforeChange": 0,
        "reviewType": "advice",
        "userDeadlines": {
            f"user:{assigned_users[0]['userAssignees'][0]['username']}": assigned_users[
                0
            ]["deadline"],
            f"user:{assigned_users[1]['userAssignees'][0]['username']}": assigned_users[
                1
            ]["deadline"],
        },
    }
    if kwargs:
        update_dictionary_from_kwargs(default_data, kwargs)

    return generate_oas_component(
        "metaobjecttypes",
        "schemas/ReviewRequest",
        **default_data,
    )


def review_document_factory(**kwargs):
    default_data = {
        "document": deepcopy(DOCUMENT_URL) + "?versie=1",
        "sourceVersion": 1,
        "reviewVersion": 2,
    }
    if kwargs:
        update_dictionary_from_kwargs(default_data, kwargs)

    return generate_oas_component(
        "metaobjecttypes",
        "schemas/Review/$defs/reviewDocument",
        **default_data,
    )


def kownsl_zaak_eigenschap_factory(**kwargs):
    default_data = {
        "url": f"{ZAAK_URL}zaakeigenschappen/c0524527-3539-4313-8c00-41358069e65b",
        "naam": "SomeEigenschap",
        "waarde": "SomeWaarde",
    }
    if kwargs:
        update_dictionary_from_kwargs(default_data, kwargs)

    return deepcopy(default_data)


def advice_factory(**kwargs):
    default_data = {
        "author": user_assignee_factory(),
        "advice": "some-advice",
        "created": "2022-04-14T15:50:09.830235Z",
        "group": dict(),
        "reviewDocuments": [review_document_factory()],
        "zaakeigenschappen": [kownsl_zaak_eigenschap_factory()],
    }
    if kwargs:
        update_dictionary_from_kwargs(default_data, kwargs)

    return generate_oas_component(
        "metaobjecttypes",
        "schemas/Review/$defs/advice",
        **default_data,
    )


def approval_factory(**kwargs):
    default_data = {
        "author": user_assignee_factory(),
        "approved": True,
        "created": "2022-04-14T15:51:09.830235Z",
        "group": dict(),
        "reviewDocuments": [review_document_factory()],
        "toelichting": "some-toelichting",
        "zaakeigenschappen": [kownsl_zaak_eigenschap_factory()],
    }
    if kwargs:
        update_dictionary_from_kwargs(default_data, kwargs)

    return generate_oas_component(
        "metaobjecttypes",
        "schemas/Review/$defs/approval",
        **default_data,
    )


def reviews_factory(**kwargs):
    default_data = {
        "id": "6a9a169e-aa6f-4dd7-bbea-6bedea74c456",
        "requester": user_assignee_factory(),
        "reviews": [advice_factory()],
        "reviewRequest": deepcopy(RR_ID),
        "reviewType": KownslTypes.advice,
        "zaak": deepcopy(ZAAK_URL),
    }
    if kwargs:
        update_dictionary_from_kwargs(default_data, kwargs)

    return generate_oas_component(
        "metaobjecttypes",
        "schemas/Review",
        **default_data,
    )


def review_request_object_type_factory(**kwargs):
    default_data = {
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
    if kwargs:
        update_dictionary_from_kwargs(default_data, kwargs)

    return generate_oas_component("objecttypes", "schemas/ObjectType", **default_data)


def review_request_object_type_version_factory(**kwargs):
    default_data = {
        "url": f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646eae/versions/4",
        "version": 4,
        "objectType": f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646eae",
        "status": "published",
        "jsonSchema": yaml.safe_load(read_schema("metaobjecttypes"))["components"][
            "schemas"
        ]["ReviewRequest"],
        "createdAt": "1999-12-31",
        "modifiedAt": "1999-12-31",
        "publishedAt": "1999-12-31",
    }
    if kwargs:
        update_dictionary_from_kwargs(default_data, kwargs)

    return generate_oas_component(
        "objecttypes", "schemas/ObjectVersion", **default_data
    )


def review_request_object_factory(**kwargs):
    default_data = {
        "url": f"{OBJECTS_ROOT}objects/85e6c250-9f51-4286-8340-25109d0b96d1",
        "uuid": "85e6c250-9f51-4286-8340-25109d0b96d1",
        "type": f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646ead",
        "record": {
            "index": 1,
            "typeVersion": 4,
            "data": review_request_factory(),
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


def review_object_type_factory(**kwargs):
    default_data = {
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
    if kwargs:
        update_dictionary_from_kwargs(default_data, kwargs)

    return generate_oas_component(
        "objecttypes",
        "schemas/ObjectType",
        **default_data,
    )


def review_object_type_version_factory(**kwargs):
    default_data = {
        "url": f"{OBJECTTYPES_ROOT}objecttypes/b3ec3f47-bc20-4872-955c-cb5f67646ead/versions/4",
        "version": 4,
        "objectType": f"{OBJECTTYPES_ROOT}objecttypes/b3ec3f47-bc20-4872-955c-cb5f67646ead",
        "status": "published",
        "jsonSchema": yaml.safe_load(read_schema("metaobjecttypes"))["components"][
            "schemas"
        ]["Review"],
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


def review_object_factory(**kwargs):
    default_data = {
        "url": f"{OBJECTS_ROOT}objects/85e6c250-9f51-4286-8340-25109d0b96d1",
        "uuid": "85e6c250-9f51-4286-8340-25109d0b96d1",
        "type": f"{OBJECTTYPES_ROOT}objecttypes/b3ec3f47-bc20-4872-955c-cb5f67646ead",
        "record": {
            "index": 1,
            "typeVersion": 4,
            "data": reviews_factory(),
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
