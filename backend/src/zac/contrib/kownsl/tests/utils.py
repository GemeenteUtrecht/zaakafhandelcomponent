from ..constants import KownslTypes

ZAKEN_ROOT = "https://zaken.nl/"
KOWNSL_ROOT = "https://kownsl.nl/"
DOCUMENTS_ROOT = "https://drc.nl/"
CATALOGI_ROOT = "http://ztc.nl/"

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
    "created": "2022-04-14T15:49:09.830235Z",
    "id": "14aec7a0-06de-4b55-b839-a1c9a0415b46",
    "forZaak": ZAAK_URL,
    "reviewType": KownslTypes.advice,
    "documents": [],
    "frontendUrl": f"{KOWNSL_ROOT}kownsl/14aec7a0-06de-4b55-b839-a1c9a0415b46/",
    "numAdvices": 1,
    "numApprovals": 0,
    "numAssignedUsers": 1,
    "openReviews": [
        {
            "deadline": "2022-04-15",
            "users": ["user:some-other-author"],
            "groups": [],
        }
    ],
    "toelichting": "some-toelichting",
    "userDeadlines": {
        "user:some-author": "2022-04-14",
        "user:some-other-author": "2022-04-15",
    },
    "requester": {
        "username": "some-user",
        "firstName": "",
        "lastName": "",
        "fullName": "",
    },
    "metadata": {
        "taskDefinitionId": "submitAdvice",
        "processInstanceId": "6ebf534a-bc0a-11ec-a591-c69dd6a420a0",
    },
    "zaakDocuments": [ZAAK_DOCUMENT],
    "reviews": [],
    "locked": False,
    "lockReason": "",
}

ADVICE = {
    "created": "2022-04-14T15:50:09.830235Z",
    "author": {
        "username": "some-author",
        "firstName": "",
        "lastName": "",
        "fullName": "",
    },
    "group": "",
    "advice": "some-advice",
    "documents": [{"document": DOCUMENT_URL, "sourceVersion": 1, "adviceVersion": 2}],
}

APPROVAL = {
    "created": "2022-04-14T15:51:09.830235Z",
    "author": {
        "username": "some-author",
        "firstName": "",
        "lastName": "",
        "fullName": "",
    },
    "group": "",
    "approved": True,
    "toelichting": "some-toelichting",
}
