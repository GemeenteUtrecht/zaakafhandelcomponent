.. _OudBehandelaren:

OudBehandelaren
===============

A ``OudBehandelaren`` objecttype stores data on historical ZAAK "behandelaren" for audit reasons.
The current implementation of the ``OudBehandelaren`` objecttype:

.. code-block:: json

    {
        "type":"object",
        "title":"OudBehandelaren",
        "required":[
            "oudbehandelaren",
            "zaak"
        ],
        "properties":{
            "zaak":{
                "type":"string"
            },
            "oudbehandelaren":{
                "type":"array",
                "items":{
                    "type":"object",
                    "title":"oudbehandelaar",
                    "required":[
                    "email",
                    "ended",
                    "started",
                    "identificatie"
                    ],
                    "properties":{
                    "email":{
                        "type":"string"
                    },
                    "ended":{
                        "type":"string"
                    },
                    "started":{
                        "type":"string"
                    },
                    "changedBy":{
                        "type":"string"
                    },
                    "identificatie":{
                        "type":"string"
                    }
                    }
                }
            }
        }
    }