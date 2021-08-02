.. _config:

=============
Configuration
=============

After deploying the ZAC, you need some runtime configuration. An administrator can
do this.

Configuring the services
========================

The ZAC does not copy data, but reads it from the external APIs. These APIs need to be
configured.

Most API's are added as services under **ZGW_Consumers > Services** in the admin
interface.

API's for Zaakgericht werken
----------------------------

Add the following services:

* Catalogi API
* Zaken API
* Documents API
* Notifications API

You will need a client ID and secret for each of those, consult the administrator for
each API for those.

Camunda process engine
----------------------

Navigate to **Camunda configuration** in the admin and fill out the details.

BRP configuration
-----------------

If you make use of HaalCentraal BRP objects, you'll need to configure the BRP API.
Navigate to **BPRconfiguratie** in the admin and verify/fill out the fields.

The service for BRP should have the following properties:

- Type: ORC (Overige)
- Authorization type: API Key or none

Header key and value should be configured according to the instructions of of the BRP
API provider.

Kadaster configuration
----------------------

If you make use of BAG objects, you'll need to configure the Kadaster APIs. Navigate
to **Kadasterconfiguratie** in the admin and verify/fill out the fields.

Kownsl
------

`Kownsl`_ manage advices and approvals. Add a **Service** for it:

- Type: ORC (Overige)
- Authorization type: API Key
- Header key: ``Authorization``
- Header value: ``Token <insert kownsl token>``

Open Forms
----------

Open Forms is a form builder engine, for which the ZAC has some basic support at the
moment. Add a **Service** for it:

- Type: ORC (Overige)
- Authorization type: API Key
- Header key: ``Authorization``
- Header value: ``Token <insert open forms token>``

Object and Objecttypes
----------------------

In order to search for objects and relate objects to a zaak, an object and objecttypes API have to be configured.
One needs to add a **Service** for each of them:

- Type: ORC (Overige)
- Authorization type: API Key
- Header key: ``Authorization``
- Header value: ``Token <insert open forms token>``

.. note::
    The object API (at least up to v1.1.1) and objecttype API (at least up to v1.1.0) included ``/api/v1`` as part of the path of all endpoints (check the API schemas `here`_).
    This means that the field ``API root url`` should **NOT** include ``/api/v1``. For example, it should be https://objecttypes.nl/
    and not https://objecttypes.nl/api/v1.

After configuring the services, the global configuration should be updated to point to a default service for both the
object and objecttype API. This can be done in the admin ``admin/core/coreconfig/``,
by updating the fields ``Primary objects API`` and ``Primary objecttypes API``.


Subscribing to notifications
============================

The ZAC is aimed at performance, and for that reason, results of API calls are cached.
Certain events require cache invalidation, and these events are received from the
Notifications API.

After installation and configuration of the servers, run the following command in
a container:

.. code-block:: bash

    src/manage.py subscribe_notifications https://zac.gemeente.nl

This will set up the ZAC to receive notifications sent from the other APIs and act
accordingly.

.. _Kownsl: https://github.com/GemeenteUtrecht/kownsl
.. _here: https://objects-and-objecttypes-api.readthedocs.io/en/latest/api/index.html
