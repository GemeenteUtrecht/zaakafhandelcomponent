===============
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
  from the case to create an advice request, and allows selection of assignees

- ``zac:configureApprovalRequest``: presents a form to the end user to select documents
  from the case to create an approval request, and allows selection of assignees

- ``zac:doRedirect``: grabs the ``redirectTo`` process variable, and redirects the user
  to this location. A ``?state`` parameter is added for the receiving application, which
  is consumed when the external application redirects the user back to the ZAC.

Form definition
---------------

Camunda allows a user task to contain a simple form definition with primitive fields.
These fields are implemented in the ZAC, and if such a form definition is present,
the ZAC renders a form for the user to fill out. Upon submission, the user task receives
the field values as process variables and the task is marked as completed.

Open Forms integration
======================

WIP
