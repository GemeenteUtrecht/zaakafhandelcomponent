.. _metaobjecttypes:

Meta ObjectTypes
================

The ZAC has custom add-on features built that require the specific meta objecttypes to be specified.

.. _Checklist:

Checklist
---------

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

.. _ChecklistType:

ChecklistType
-------------

A checklisttype defines the shape of a checklist. The checklisttype can be attributed to multiple zaaktypes, but any zaaktype shouldn't have 
more than one checklisttype. Currently, the checklisttype objecttype is defined as below:

.. code-block:: json

    {
        "type":"object",
        "title":"ChecklistType",
        "required":[
            "zaaktypeCatalogus",
            "zaaktypeIdentificaties",
            "questions",
            "meta"
        ],
        "properties":{
            "meta":true,
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

.. _OudBehandelaren:

OudBehandelaren
---------------

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
            "meta":true,
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
                    "identificatie":{
                        "type":"string"
                    }
                    }
                }
            }
        }
    }

.. _StartCamundaProcessForm:

StartCamundaProcessForm
-----------------------

To expedite ``Zaak`` process preconfiguration, a ``StartCamundaProcessForm`` can be linked to a ``ZaakType``.
The ``StartCamundaProcessForm`` will take care of guiding the user into providing the values necessary for the starting the business process related to the ``Zaak``.
The current implementation of ``StartCamundaProcessForm``:

.. code-block:: json

    {
        "type":"object",
        "title":"StartCamundaProcessForm",
        "required":[
            "meta",
            "zaaktypeCatalogus",
            "zaaktypeIdentificaties",
            "camundaProcessDefinitionKey",
            "processEigenschappen",
            "processRollen",
            "processInformatieObjecten"
        ],
        "properties":{
            "meta":true,
            "processRollen":{
                "type":"array",
                "items":{
                    "type":"object",
                    "title":"processRol",
                    "required":[
                    "roltypeOmschrijving",
                    "betrokkeneType",
                    "label",
                    "required",
                    "order"
                    ],
                    "properties":{
                    "label":{
                        "type":"string"
                    },
                    "order":{
                        "type":"integer"
                    },
                    "required":{
                        "type":"boolean"
                    },
                    "betrokkeneType":{
                        "enum":[
                            "natuurlijk_persoon",
                            "niet_natuurlijk_persoon",
                            "vestiging",
                            "organisatorische_eenheid",
                            "medewerker"
                        ],
                        "type":"string"
                    },
                    "roltypeOmschrijving":{
                        "type":"string"
                    }
                    }
                }
            },
            "zaaktypeCatalogus":{
                "type":"string"
            },
            "processEigenschappen":{
                "type":"array",
                "items":{
                    "type":"object",
                    "title":"processEigenschap",
                    "required":[
                    "eigenschapnaam",
                    "label",
                    "default",
                    "required",
                    "order"
                    ],
                    "properties":{
                    "label":{
                        "type":"string"
                    },
                    "order":{
                        "type":"integer"
                    },
                    "default":{
                        "type":"string"
                    },
                    "required":{
                        "type":"boolean"
                    },
                    "eigenschapnaam":{
                        "type":"string"
                    }
                    }
                }
            },
            "zaaktypeIdentificaties":{
                "type":"array",
                "items":{
                    "type":"string"
                }
            },
            "processInformatieObjecten":{
                "type":"array",
                "items":{
                    "type":"object",
                    "title":"processInformatieObject",
                    "required":[
                    "informatieobjecttypeOmschrijving",
                    "allowMultiple",
                    "label",
                    "required",
                    "order"
                    ],
                    "properties":{
                    "label":{
                        "type":"string"
                    },
                    "order":{
                        "type":"integer"
                    },
                    "required":{
                        "type":"boolean"
                    },
                    "allowMultiple":{
                        "type":"boolean"
                    },
                    "informatieobjecttypeOmschrijving":{
                        "type":"string"
                    }
                    }
                }
            }
        }
    }

.. _ZaakTypeAttribute:

ZaakTypeAttribute
-----------------

A ``ZaakTypeAttribute`` objecttype allows for a flexible ``enum`` object related to a ``ZaakType.eigenschap``.
As such, the ZAC will try to corroborate the value of the ``ZaakType.eigenschap`` to a value in the ``ZaakTypeAttribute``.
The current implementation of the ``ZaakTypeAttribute`` objecttype:

.. code-block:: json

    {
        "type":"object",
        "title":"ZaaktypeAttributen",
        "required":[
            "naam",
            "waarde",
            "zaaktypeIdentificaties",
            "zaaktypeCatalogus",
            "meta"
        ],
        "properties":{
            "enum":{
                "type":"array",
                "items":{
                    "type":"string"
                }
            },
            "meta":true,
            "naam":{
                "type":"string"
            },
            "waarde":{
                "type":"string"
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