.. _forms:

Available forms
===============

The ZAC presents some (dynamically generated) forms to its users.

Camunda forms
=============

The ZAC handles two distinct flavours of form definitions: form key based, or form
definition based. If a form key is present for a task, then this will be used. If
it's absent, then the form definition is used.

Form keys
---------

A Camunda user task can contain a form key reference. The following form keys are
implemented by the ZAC:

- ``zac:configureAdviceRequest``: presents a form to the end user to select documents
  from the case to create an advice request, and allows selection of assignees.

  Upon succesful submission, the following process variables are set:

    - ``kownslUsers``: a (JSON) list of user identifiers, e.g.: ``["marte004", "beer001"]``
    - ``kownslReviewRequestId``: a (String) reference to the Kownsl review request created.
    - ``kownslFrontendUrl``: the URL for end users to submit their advice.
    - ``kownslDocuments``: a (JSON) list of document urls, e.g.: ``["https://drc.cg-intern.utrecht.nl/api/v1/enkelvoudiginformatieobjecten/<uuid1>", "https://drc.cg-intern.utrecht.nl/api/v1/enkelvoudiginformatieobjecten/<uuid2>"]``.
    - ``emailNotificationList``: a JSON of usernames or groupnames with an email notification flag (boolean).

- ``zac:configureApprovalRequest``: presents a form to the end user to select documents
  from the case to create an approval request, and allows selection of assignees.

  Upon succesful submission, the following process variables are set:

    - ``kownslUsers``: a (JSON) list of user identifiers, e.g.: ``["marte004", "beer001"]``
    - ``kownslReviewRequestId``: a (String) reference to the Kownsl review request created.
    - ``kownslFrontendUrl``: the URL for end users to submit their approval.
    - ``kownslDocuments``: a (JSON) list of document urls, e.g.: ``["https://drc.cg-intern.utrecht.nl/api/v1/enkelvoudiginformatieobjecten/<uuid1>", "https://drc.cg-intern.utrecht.nl/api/v1/enkelvoudiginformatieobjecten/<uuid2>"]``.
    - ``emailNotificationList``: a JSON of usernames or groupnames with an email notification flag (boolean).

- ``zac:doRedirect``: grabs the ``redirectTo`` process variable, and redirects the user
  to this location. A ``?state`` parameter is added for the receiving application, which
  is consumed when the external application redirects the user back to the ZAC.

  If you set the proces/task variable ``openInNewWindow`` to the boolean "true" value,
  then the page will be opened in a new tab or window, and the end-user can mark the
  task as completed.

- ``zac:documentSelectie``: presents a form to the end user to select documents for the camunda process.

  Upon succesful submission, the following process variables are set:
    
    - ``documenten``: a (JSON) list of document urls, e.g.: ``["https://drc.cg-intern.utrecht.nl/api/v1/enkelvoudiginformatieobjecten/<uuid1>", "https://drc.cg-intern.utrecht.nl/api/v1/enkelvoudiginformatieobjecten/<uuid2>"]``.

Form definition
---------------

Camunda allows a user task to contain a simple form definition with primitive fields.
These fields are implemented in the ZAC, and if such a form definition is present,
the ZAC renders a form for the user to fill out. Upon submission, the user task receives
the field values as process variables and the task is marked as completed.

Open Forms integration
======================

WIP
