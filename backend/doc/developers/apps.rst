.. _django-apps-configuration:

Django apps
===========

The ZAC is a Django project made up of a number of Django *apps*.

``zac.accounts``
----------------

Deals with user authentication and permissions.

``zac.activities``
------------------

Deals with ad-hoc activities for cases.

``zac.api``
-----------

Top level backend-for-frontend (BFF) API entrypoint.

Use this for:

* project level URL routing
* project level django-rest-framework utilities/extensions

There should not be any concrete views, serializers, fields... defined here, only
base classes.

``zac.camunda``
---------------

Intended for interaction/bindings with the Camunda process engine. This should be seen
as an extension of django-camunda.

``zac.camunda`` deals with Camunda concepts and offers pluggable interfaces to specific
Camunda concepts, such as dynamic forms defined in BPMN process models.

If you find yourself *using* the pluggable interfaces inside of this app, there's
probably a better, more specific app for that.

``zac.contrib``
---------------

Integrations with (usually) optional external APIs that add value to the core of
case-oriented working. Often these are specific commercial products, such as
ValidSign, Xential... or highly specific components.

``zac.core``
------------

Intended for all interaction with the core of case-oriented working, which entails the
standards as determined by VNG.

Usually contrib apps depend on functionality from the core app, not the other way around.

``zac.elasticsearch``
---------------------

Intended for interfacing with Elasticsearch search index. To the outside world, we
'hide' this implementation detail. Other apps should not interface directly with
elastic search, but rather interface through this app for particular searches.

This keeps the backend pluggable - if we need to look at alternatives, we only have to
swap out a single app.

``zac.notifications``
---------------------

Deal with incoming notifications and subscriptions on notification channels.

``zac.werkvoorraad``
--------------------

Aggregate the "workload" for an end-user.
