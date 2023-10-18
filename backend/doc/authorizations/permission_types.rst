.. _permission-types:

Permission types
================

Each permission has the object type the permission relates to. For now three object types are supported:

* ``ZAAK`` (case)
* ``INFORMATIEOBJECT`` (document)

Each object type has its required shape for a blueprint permission.
It is explained in the details in :ref:`authorization_blueprints`.

Each permission provides the right to perform one of the following types of operations:

* zaak permissions:
    * ``activiteiten:inzien`` - to read activities of the ``ZAAK``.
    * ``activiteiten:schrijven`` - to add activities to the ``ZAAK``.
    * ``checklist:inzien`` - to view a ``CHECKLIST`` of the ``ZAAK``.
    * ``checklist:schrijven`` - to edit a ``CHECKLIST`` of the ZAAK.
    * ``checklisttypes:inzien`` - to view the ``CHECKLISTTYPE`` of the ``ZAAK``.
    * ``checklisttypes:schrijven`` - to edit the ``CHECKLISTTYPE`` of the ``ZAAK``.
    * ``zaken:aanmaken`` - to create the ``ZAAK``.
    * ``zaken:add-documents`` - to add ``INFORMATIEOBJECTs`` to the ``ZAAK``.
    * ``zaken:afsluiten`` - to end the ``ZAAK``.
    * ``zaken:create-status`` - to set a ``STATUS`` on the ``ZAAK``.
    * ``zaken:geforceerd-bijwerken`` - to force edit the ``ZAAK`` (after setting a ``RESULTAAT``).
    * ``zaken:inzien`` - to see the ``ZAAK`` details.
    * ``zaken:lijst-documenten`` - to view the list of ``INFORMATIEOBJECTs`` related to the ``ZAAK``.
    * ``zaken:nieuwe-relaties-toevoegen`` - to add new relations to the ``ZAAK``.
    * ``zaken:set-result`` - to set a ``RESULTAAT`` on a ``ZAAK``.
    * ``zaken:toegang-aanvragen`` - to request access to the ``ZAAK``.
    * ``zaken:toegang-verlenen`` - to manage access to the ``ZAAK``.
    * ``zaken:wijzigen`` - to modify the ``ZAAK`` for example to change the confidentiality level.
    * ``zaakproces:starten`` - to start a process related to the ``ZAAK`` in camunda.
    * ``zaakproces:usertasks-uitvoeren`` - to perform Camunda tasks.
    * ``zaakproces:send-bpmn-message`` - to send messages in the Camunda process.

* document permissions:
    * ``zaken:download-documents`` - to see the metadata and content of the document.
    * ``zaken:update-documents`` - to update the content of the document.

The permissions used only in the old version of the ZAC:

* zaak permissions:
    * ``zaken:afsluiten`` - to close the ``ZAAK``.
    * ``zaken:set-result`` - to set result to the ``ZAAK``.
    * ``zaken:create-status`` - to add status to the ``ZAAK``.


They can be grouped into roles for blueprint permissions.
It is explained in the details in the "Blueprint permission" subsection.