KOWNSL implementation
=====================

The KOWNSL implementation has become so interweaved with the ZAC that it requires its own documentation.
There are two flavors of review request. 

* Advice (Advies vragen)
* Approval (Akkoord vragen)

Starting a review request from the ZAC
--------------------------------------

A user initiaties an "Advies vragen" or "Akkoord vragen" action from the zaak-detail page under the tab "Acties".
This sends a message to the relevant camunda message and starts a subprocess event. 
The subprocess event will, if not predefined in the BPMN model itself, then ask for the review request to be configured.

The configuration includes setting which documents are to be reviewed, which users are responsible for reviewing, when their deadline
is and if they should be sent an email notification about the request.


Updating a review request from the ZAC
--------------------------------------

A review request can get locked or have its assigned users changed. In both cases the process instance in Camunda will be killed
and reviewers are notified through an email if they are flagged to receive an email notification at the configuration step.

A user puts in a lock or update users request through the relevant endpoint and states the reason if required.
The review request gets updated in the KOWNSL app.
The KOWNSL app sends a notification to Open Notifications that the review request is updated with the relevant *kenmerken*: `locked` and/or `updatedAssignedUsers`.
Open Notifications sends out a notification to all relevant subscribers with the given *kenmerken*.
The ZAC reads the notification and sends out a message (kill-process or change-process) which kills the BPMN process.
If a process is changed, the BPMN model will feedback a new review request configuration *actie* on the zaak-detail page in which the old users are shown 
and the new users are to be configured.

The process then repeats itself.

A review request gets updated
-----------------------------

A review request can also be updated from within the KOWNSL application itself. Django pre- and post-save signals in KOWNSL should
kick off the relevant notification processes that then instruct the ZAC to do as is explained under **Updating a review request from the ZAC**.