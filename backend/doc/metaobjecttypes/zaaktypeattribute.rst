.. _ZaakTypeAttribute:

ZaakTypeAttribute
=================

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