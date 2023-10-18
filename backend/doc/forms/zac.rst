.. _zac-forms:

ZAC forms (form key)
====================

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

- ``zac:documentSelectie``: presents a form to the end user to select documents for the camunda process.

  Upon succesful submission, the following process variables are set:
    
    - ``documenten``: a (JSON) list of document urls, e.g.: ``["https://drc.cg-intern.utrecht.nl/api/v1/enkelvoudiginformatieobjecten/<uuid1>", "https://drc.cg-intern.utrecht.nl/api/v1/enkelvoudiginformatieobjecten/<uuid2>"]``.

- ``zac:doRedirect``: grabs the ``redirectTo`` process variable, and redirects the user
  to this location. A ``?state`` parameter is added for the receiving application, which
  is consumed when the external application redirects the user back to the ZAC.

  If you set the proces/task variable ``openInNewWindow`` to the boolean "true" value,
  then the page will be opened in a new tab or window, and the end-user can mark the
  task as completed.

  If you set the process/task variable ``endTask`` to the boolean "false" value the 
  user will not see a window that allows them to finish the task. This is used
  in the current implementation for opening a related ZAAK from the main ZAAK.

- ``zac:startProcessForm``: grabs the URL-reference to the ZAAK in Open Zaak from 
  the camunda process and uses it to fetch the appropriate form from the Objects API
  that holds the data template required to be filled in to start the camunda process.

- ``zac:zetResultaat``: this forms allows a number of checks to be done before a RESULTAAT is set on a ZAAK.
  URL-reference to the ZAAK in Open Zaak is grabbed and then the form feeds back all related
  open activities, checklist questions, camunda tasks, review requests and open documents to 
  the user. It also allows the user to select what the RESULTAAT should be based of the RESULTAATTYPEs
  related to the ZAAK.