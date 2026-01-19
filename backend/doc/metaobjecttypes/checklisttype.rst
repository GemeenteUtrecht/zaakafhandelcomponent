.. _ChecklistType:

ChecklistType
=============

A checklisttype defines the shape of a checklist. The checklisttype can be attributed to multiple zaaktypes, but any zaaktype shouldn't have 
more than one checklisttype. Currently, the checklisttype objecttype is defined as below:

.. code-block:: json

    {
        "type":"object",
        "title":"ChecklistType",
        "required":[
            "zaaktypeCatalogus",
            "zaaktypeIdentificaties",
            "questions"
        ],
        "properties":{
            "questions":{
                "type":"array",
                "items":{
                    "type":"object",
                    "title":"ChecklistQuestion",
                    "required":[
                    "question",
                    "choices",
                    "order"
                    ],
                    "properties":{
                    "order":{
                        "type":"integer"
                    },
                    "choices":{
                        "type":"array",
                        "items":{
                            "type":"object",
                            "properties":{
                                "name":{
                                "type":"string"
                                },
                                "value":{
                                "type":"string"
                                }
                            }
                        }
                    },
                    "question":{
                        "type":"string"
                    }
                    }
                }
            },
            "zaaktypeCatalogus":{
                "type":"string"
            },
            "zaaktypeIdentificaties":{
                "type":"array",
                "items":{
                    "type":"string"
                }
            }
        }
    }