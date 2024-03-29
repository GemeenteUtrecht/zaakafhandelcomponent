.. _StartCamundaProcessForm:

StartCamundaProcessForm
=======================

To expedite ``Zaak`` process preconfiguration, a ``StartCamundaProcessForm`` can be linked to a ``ZaakType``.
The ``StartCamundaProcessForm`` will take care of guiding the user into providing the values necessary for the starting the business process related to the ``Zaak``.
The current implementation of ``StartCamundaProcessForm``:

.. code-block:: json

    {
        "type":"object",
        "title":"StartCamundaProcessForm",
        "required":[
            "zaaktypeCatalogus",
            "zaaktypeIdentificaties",
            "camundaProcessDefinitionKey",
            "processEigenschappen",
            "processRollen",
            "processInformatieObjecten"
        ],
        "properties":{
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