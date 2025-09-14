OBJECTTYPES_ROOT = "http://objecttype.nl/api/v2/"
OBJECTS_ROOT = "http://object.nl/api/v2/"

METALIST_OBJECTTYPE = {
    "url": f"{OBJECTTYPES_ROOT}objecttypes/a9410e3ff-adc0-42ae-9c39-c86d501950a7/versions/4",
    "version": 4,
    "objectType": f"{OBJECTTYPES_ROOT}objecttypes/a9410e3ff-adc0-42ae-9c39-c86d501950a7",
    "status": "published",
    "jsonSchema": {
        "type": "object",
        "title": "MetaListObjectType",
        "properties": {
            "metaobjecttypes": {
                "type": "object",
            }
        },
    },
    "createdAt": "1999-12-31",
    "modifiedAt": "1999-12-31",
    "publishedAt": "1999-12-31",
}

METALIST_OBJECT = {
    "url": f"{OBJECTS_ROOT}objects/dba0e276-2347-44e3-9965-9956334ac4ff",
    "uuid": "dba0e276-2347-44e3-9965-9956334ac4ff",
    "type": f"{OBJECTTYPES_ROOT}objecttypes/a9410e3ff-adc0-42ae-9c39-c86d501950a7",
    "record": {
        "index": 1,
        "typeVersion": 4,
        "data": {"metaobjecttypes": dict()},
        "geometry": "None",
        "startAt": "1999-12-31",
        "endAt": "None",
        "registrationAt": "1999-12-31",
        "correctionFor": "None",
        "correctedBy": "None",
    },
}
