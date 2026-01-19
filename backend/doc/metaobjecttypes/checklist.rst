.. _Checklist:

Checklist
=========

A checklist object is a series of questions, answers and possibly supportive evidence such as comments or documents.
The checklist is defined by a :ref:`ChecklistType`.
Any zaak can only have zero or one checklist(s). 
With the request autosave functionality of the checklist, checklists locks are enforced from within the ZAC to prevent a cascade of object record creation.

Current implementation of a checklist objecttype:

.. code-block:: json

    {
        "type":"object",
        "$defs":{
            "user":{
                "type":[
                    "null",
                    "object"
                ],
                "title":"user",
                "required":[
                    "username",
                    "firstName",
                    "fullName",
                    "lastName",
                    "email"
                ],
                "properties":{
                    "email":{
                    "type":"string"
                    },
                    "fullName":{
                    "type":"string"
                    },
                    "lastName":{
                    "type":"string"
                    },
                    "username":{
                    "type":"string"
                    },
                    "firstName":{
                    "type":"string"
                    }
                }
            },
            "group":{
                "type":[
                    "null",
                    "object"
                ],
                "title":"group",
                "required":[
                    "name",
                    "fullName"
                ],
                "properties":{
                    "name":{
                    "type":"string"
                    },
                    "fullName":{
                    "type":"string"
                    }
                }
            },
            "answer":{
                "type":"object",
                "title":"ChecklistAnswer",
                "required":[
                    "question",
                    "answer",
                    "created"
                ],
                "properties":{
                    "answer":{
                    "type":"string"
                    },
                    "created":{
                    "type":"string"
                    },
                    "remarks":{
                    "type":"string"
                    },
                    "document":{
                    "type":"string"
                    },
                    "question":{
                    "type":"string"
                    },
                    "userAssignee":{
                    "$ref":"#/$defs/user"
                    },
                    "groupAssignee":{
                    "$ref":"#/$defs/group"
                    }
                }
            }
        },
        "title":"Checklist",
        "required":[
            "answers",
            "zaak",
            "locked"
        ],
        "properties":{
            "zaak":{
                "type":"string"
            },
            "locked":{
                "type":"boolean",
                "value":false
            },
            "answers":{
                "type":"array",
                "items":{
                    "$ref":"#/$defs/answer"
                }
            }
        }
    }
