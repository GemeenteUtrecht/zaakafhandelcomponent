.. _config-services:

Services
========

The ZAC reads data from the external APIs. These APIs need to be
configured. For performance some of the data is copied into a read-only 
elasticsearch database.

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

BPTL configuration
------------------

The camunda process engine implements two basic tasks: user and service tasks.
Camunda makes use of the BPTL (Business Process Task Library) to handle the service tasks.
A service task is set in a queue from where the BPTL will fetch and process the task.
Some service tasks require information from the ZAC. To allow the BPTL to access information
from the ZAC please create an ApplicationToken in the ZAC and configure the ApplicationToken
in the BPTL as such:

- Type: ORC (Overige)
- Authorization type: API Key
- Header key: ``Authorization``
- Header value: ``ApplicationToken <insert BPTL token>``

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

`Kownsl`_ manages advices and approvals. Add a **Service** for it:

- Type: ORC (Overige)
- Authorization type: ZGW client_id + secret
- Client id: ``some-kownsl-id``
- Client secret: ``some-kownsl-secret``

DoWC
----

`DoWC`_ allows documents to be opened and edited by using the MS Office WebDAV features. Add a **Service** for it:

- Type: ORC (Overige)
- Authorization type: API Key & ZGW client_id + secret
- Client id: ``some-dowc-id``
- Client secret: ``some-dowc-secret``
- Header key: ``Authorization``
- Header value: ``ApplicationToken <insert DoWC token>``

.. note::
    The DoWC must be configured to communicate with the same DRC API(s) as the ZAC. The DoWC uses
    the ZGW client to support username claims in the JWTToken but allows an application like the ZAC
    to communicate directly through an ApplicationToken Authorization header as well.

Object and Objecttypes
----------------------

The object(types) APIs are not only used for physical objects related to ZAAKs but also to store meta-data
of ZAAKs for which Open Zaak does not accomodate, e.g. old case managers, checklists, ZAAKTYPE-attributes and
camunda forms related to kickstarting a camunda process related to a ZAAK.
In order to search for objects and relate objects to a zaak, an object and objecttypes API have to be configured.
One needs to add a **Service** for each of them:

- Type: ORC (Overige)
- Authorization type: API Key
- Header key: ``Authorization``
- Header value: ``Token <insert open forms token>``

.. note::
    The object API (at least up to v1.1.1) and objecttype API (at least up to v1.1.0) included ``/api/v1`` as part of the path of all endpoints (`objects-and-objecttypes-api`_ API schemas).
    This means that the field ``API root url`` should **NOT** include ``/api/v1``. For example, it should be https://objecttypes.cg-intern.utrecht.nl/
    and not https://objecttypes.cg-intern.utrecht.nl/api/v1.

After configuring the services, the global configuration should be updated to point to a default service for both the
object and objecttype API. This can be done in the admin ``admin/core/coreconfig/``,
by updating the fields ``Primary objects API`` and ``Primary objecttypes API``.

.. _Kownsl: https://kownsl.cg-intern.utrecht.nl/api/v1/docs/
.. _DoWC: https://dowc.cg-intern.utrecht.nl/api/v1/docs/
.. _objects-and-objecttypes-api: https://objects-and-objecttypes-api.readthedocs.io/en/latest/api/index.html
