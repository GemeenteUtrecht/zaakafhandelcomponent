=============
Configuration
=============

After deploying the ZAC, you need some runtime configuration. An administrator can
do this.

Configuring the services
========================

The ZAC does not copy data, but reads it from the external APIs. These APIs need to be
configured.

API's for Zaakgericht werken
----------------------------

In the admin, navigate to **ZGW_Consumers** and add the following services:

* Catalogi API
* Zaken API
* Documents API
* Notifications API

You will need a client ID and secret for each of those, consult the administrator for
each API for those.

Camunda process engine
----------------------

Navigate to **Camunda configuration** in the admin and fill out the details.

Kadaster configuration
----------------------

If you make use of BAG objects, you'll need to configure the Kadaster APIs. Navigate
to **Kadasterconfiguratie** in the admin and verify/fill out the fields.


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
