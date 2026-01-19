.. _applicationtokens:

ApplicationToken
================

To regulate permissions of applications making requests to the ZAC we have implemented an ApplicationToken which needs to be inserted in 
the header of the request from the requesting service. An ApplicationToken can be linked to an :ref:`authorization_blueprints` to manage
permissions on a granular level or given full read access.

Currently the DoWC, BPTL and Alfresco make use of the ApplicationToken to communicate with the ZAC if required.

