.. _zaak-aanmaken-troubleshooting:

Zaak aanmaken
=============

No zaaktypes available
----------------------

* Check connection with Open zaak.
* Check permissions of user.
* Invalidate cache for ZAC (management endpoint available, please refer to the API documentation).
* ZAAKTYPEs aren't published or CATALOGUS isn't available.

User doesn't get referred to ZAAK detail page
---------------------------------------------

* Check if ZAAK was created in Open Zaak.
* Check if notification was sent to and received by Open Notificaties.
* Check if notification was succesfully sent out to relevant subscribers in Open Notificaties.
* Check if the BPTL shows any errors.
* Check if Camunda is showing any errors in :ref:`zaak aanmaken bpmn <zaak-aanmaken-bpmn>`.
* Contact a developer.