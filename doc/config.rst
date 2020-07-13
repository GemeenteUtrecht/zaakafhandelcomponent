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
