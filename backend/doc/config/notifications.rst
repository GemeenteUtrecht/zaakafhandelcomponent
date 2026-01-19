.. _notifications:

Subscribing to notifications
============================

The ZAC is aimed at performance, and for that reason, results of API calls are cached.
Certain events require cache invalidation, and these events are received from the
Notifications API.

After installation and configuration of the servers, run the following command in
a container:

.. code-block:: bash

    src/manage.py subscribe_notifications https://zac.cg-intern.utrecht.nl/

This will set up the ZAC to receive notifications sent from the other APIs and act
accordingly.


Comments notifications API configuration
========================================

It is extremely important to configure the `Autorisaties` of the Open Notificaties API.
Without the correct configuration an evil/naive actor could abuse the Open Notificaties API to send abusive notifications
to those registered. An example:

Imagine a consuming service has logic attached to a notification that impacts local data or triggers an expensive operation,
a wrongfully authorized Open Notificaties Autorisaties API could allow a service that has been granted permissions it shouldn't have
to trigger those notifications. The Autorisaties API of Open Notificaties is an extra filter that allows for more granular control
over which posting service has the permissions to send a notification concerning which topics and levels.
Try not to grant services the "has all rights" without sufficient reasons to do so.

You can model the permissions based off of the Application Autorisaties as configured in the Open Zaak API.