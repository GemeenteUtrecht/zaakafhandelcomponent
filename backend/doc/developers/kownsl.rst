.. _kownsl-implementation:

Kownsl implementation
=====================

The Kownsl implementation has become so interweaved with the ZAC that it requires its own documentation.
Before March 27th of 2024 we had a separate application for Kownsl activities, which was then deprecated in favor
of a hybrid solution between the OBJECTS API (functions as a database) and the actions which are defined within the ZAC and the 
relevant Camunda BPMNs. Please see the :ref:`config-metaobjecttypes` for further information.

There are two flavors of review request. 

* Advice (Advies vragen)
* Approval (Akkoord vragen)

Starting a review request from the ZAC
--------------------------------------

A user initiates an "Advies vragen" or "Akkoord vragen" action from the zaak-detail page under the tab "Acties".
This sends a message to the relevant camunda message and starts a subprocess event. 
The subprocess event will, if not predefined in the BPMN model itself, then ask for the review request to be configured.

The configuration includes setting which documents are to be reviewed, which users are responsible for reviewing, when their deadline
is and if they should be sent an email notification about the request.


Updating a review request from the ZAC
--------------------------------------

A review request can get locked or have its assigned users changed. In both cases the process instance in Camunda will be killed
and reviewers are notified through an email if they are flagged to receive an email notification at the configuration step.

A user puts in a lock or update users request through the relevant endpoint and states the reason if required.
The review request gets updated in the OBJECTS API.
The OBJECTS API app sends a notification to Open Notifications that the review request is updated with the relevant *kenmerken*: `objectType` on *kanaal*: `objecten`.
Open Notifications sends out a notification to all relevant subscribers with the given *kenmerken*.
The ZAC reads the notification and sends out a message (kill-process or change-process) which kills the BPMN process.
If a process is changed, the BPMN model will feedback a new review request configuration *actie* on the zaak-detail page in which the old users are shown 
and the new users are to be configured.

The process then repeats itself.

A review request gets updated
-----------------------------

A review request can also be updated from within the KOWNSL application itself. Notifications from the OBJECTS API should
kick off the relevant notification processes that then instruct the ZAC to do as is explained under **Updating a review request from the ZAC**.