.. _Checklist:

Checklist
=========

A checklist object is a series of questions, answers and possibly supportive evidence such as comments or documents.
The checklist is defined by a :ref:`ChecklistType`.
Any zaak can only have zero or one checklist(s). Current implementation of a checklist objecttype:

.. code-block:: json

    {
        "type":"object",
        "title":"Checklist",
        "required":[
            "answers",
            "zaak",
            "meta",
            "lockedBy"
        ],
        "properties":{
            "meta":true,
            "zaak":{
                "type":"string"
            },
            "answers":{
                "type":"array",
                "items":{
                    "type":"object",
                    "title":"ChecklistAnswer",
                    "required":[
                    "question",
                    "answer"
                    ],
                    "properties":{
                    "answer":{
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
                        "type":[
                            "string",
                            "null"
                        ]
                    },
                    "groupAssignee":{
                        "type":[
                            "string",
                            "null"
                        ]
                    }
                    }
                }
            },
            "lockedBy":{
                "type":[
                    "string",
                    "null"
                ]
            }
        }
    }
