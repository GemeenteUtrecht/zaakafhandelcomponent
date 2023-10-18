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

