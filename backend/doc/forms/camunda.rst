.. _camunda-forms:

Camunda (form definition)
=========================

Form definition
---------------

Camunda allows a user task to contain a simple form definition with primitive fields.
These fields are implemented in the ZAC, and if such a form definition is present,
the ZAC renders a form for the user to fill out. Upon submission, the user task receives
the field values as process variables and the task is marked as completed.

Camunda can also refer to external forms. We implement external forms in the :ref:`ZAC <zac-forms>`.