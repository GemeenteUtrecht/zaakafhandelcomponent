.. _authorization:

=============
Authorization
=============

The ZAC represents the application of the 5th layer of the Common Ground architecture. It
requests and modifies information from different APIs including Zaken API, Documenten API,
Kownsl API, etc. Therefore the ZAC has implemented the authorization model which ensures that
all the ZAC users have permissions to perform necessary operations via these APIs.

Permission types
----------------
Each permission has the object type the permission relates to. For now two object types are supported:

* zaak (case)
* document

Each permission provides the right to perform one of the following types of operations:

* zaak permissions:
    * ``zaken:inzien`` - to see the case details. It's the most used permission in the ZAC
    * ``zaken:wijzigen`` - to modify the case, for example, to add documents to the case
    * ``zaakproces:usertasks-uitvoeren`` - to perform Camunda tasks
    * ``zaakproces:send-bpmn-message`` - to send messages in the Camunda process
    * ``zaken:add-documents`` - to add documents to the case
    * ``zaken:nieuwe-relaties-toevoegen`` - to add new relations to the case
    * ``zaken:toegang-aanvragen`` - to request access to the case
    * ``zaken:toegang-verlenen`` - to manage access to the case
    * ``activities:read`` - to read activities of the case
    * ``activiteiten:schrijven`` - to add activities to the case

* document permissions:
    * ``zaken:download-documents`` - to see the metadata and content of the document
    * ``zaken:update-documents`` - to update the content of the document


The permissions used only in the old version of the ZAC:

* zaak permissions:
    * ``zaken:afsluiten`` - to close the case.
    * ``zaken:set-result`` - to set result to the case
    * ``zaken:create-status`` - to add status to the case

Each operation type has its own required shape for a blueprint permission.
It is explained in the details in the "Blueprint permission" subsection.

Blueprint permissions
---------------------

The permissions in the ZAC can be divided into two groups:

* blueprint permissions
* atomic permissions.

Blueprint permission allows a user to perform a particular operation on the defined subset of the objects.
This is the main type of the permissions. Blueprint permissions are defined by functional managers
in the admin interface of the ZAC. The user interface to manage them in the app is **WIP**.

The subset of the objects (or "blueprint") is defined based on object properties and unique for every permission type.

For now two blueprints are supported:

* for zaak permissions:
    * zaaktype (``catalogus`` and ``omschrijving``)
    * maximum confidential level (``vertrouwelijkheidaanduiding``)

* for document permissions:
    * informatieobjecttype (``catalogus`` and ``omschrijving``)
    * maximum confidential level (``vertrouwelijkheidaanduiding``)

The new blueprints can be easily defined for all kind of objects and their properties.

Authorization profiles
----------------------

Blueprint permissions can be grouped into authorization profiles which represent "roles" in the ZAC
authorization model. Each user can relate to one of many authorization profiles. Therefore it is
possible to create several profiles with typical permission groups (read-only, admin, etc.) and then
to relate users to them.

Like blueprint permissions authorization profiles are also managed by functional managers in the ZAC admin.

Atomic permissions
------------------

Sometimes users should have extra permissions for particular objects. For example, user John has
blueprint permission to read all the cases of the "Beleid opstellen" case type. But one of these
cases has a related case with another case type ("Bestuurlijke besluitvorming"). So John can
request access for the particular case and he will be able to see only one case of this case type.

Unlike blueprint permissions there are several sources of the atomic permissions for the users:

* the user is a **behandelaar** of the case. When this role is created (and the notification is received
  by the ZAC) the user receives a permission to read the case automatically.
* the user is required to be an **adviser** or **approver** of the case. When the review request is created
  the users mentioned there receive a permission to read the case automatically.
* the user is assigned to a case **activity**. When the user is assigned to the activity they
  receive permissions to read and update activities automatically.
* the user **requested access** to the particular case and this request was approved.
* the functional manager created an atomic permission in the admin (not recommended).

The display of all the users and their atomic permissions for the case in the ZAC is **WIP** now.
