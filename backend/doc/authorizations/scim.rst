.. _authorization_scim:

SCIM Interface (N/A)
====================

IMPLEMENTION ON HOLD AND CURRENTLY NOT AVAILABLE


The System for Cross-domain Identity Management (SCIM) is an `open standard <https://datatracker.ietf.org/doc/html/rfc7644>`_
to help automating the management of users within a company.
It was introduced to address the problem faced by companies with a large number of employees, where
creating, deleting and updating the permissions of users accounts takes considerable time for the IT department.
The idea is that users should be managed in a central place and then communicated to various apps through the SCIM API.
The 'central place' is usually referred to as the "Identity Provider" while the apps or other services are the
"Service Providers".

SCIM provides a `standardised <https://datatracker.ietf.org/doc/html/rfc7643#section-3>`_ way of representing **users** and
**groups**, as well as other resource types, in a JSON format.
The users associated with a group are part of the JSON data of that particular group and are referred to as "members".
This schema makes it easy to exchange users/group information between the Identity Provider and the Service Providers.


The SCIM API in ZAC (N/A)
^^^^^^^^^^^^^^^^^^^^^^^^^

IMPLEMENTION ON HOLD AND CURRENTLY NOT AVAILABLE


In ZAC, the ``User`` and the ``AuthorizationProfile`` models are exposed through
the `SCIM 2.0 <http://www.simplecloud.info/>`_ interface. The information contained in the ``User`` model and the
``AuthorizationProfile`` model is converted to the JSON format expected for SCIM resources of type ``User`` and ``Group``
respectively.
Since each ``AuthorizationProfile`` is linked to one or more users, when it is converted to the JSON format these users
will be visible in the ``members`` attribute.

Through this API, it is then possible to:

1. Add, delete, search for, read and modify users in ZAC
2. Search for and read authorization profiles
3. Add/remove the relation between a user and an authorization profile

More information about the endpoints can be found `here <https://datatracker.ietf.org/doc/html/rfc7644#section-3.2>`_.

For the ``/scim/v2/Users/.search`` endpoint, the fields on which it is possible to filter are:

- ``userName``
- ``name`` (searches in both Django ``User`` attributes ``first_name`` and ``last_name``)
- ``familyName`` (filters by Django ``User`` attribute ``last_name``)
- ``givenName`` (filters by Django ``User`` attribute ``first_name``)
- ``active`` (filters by Django ``User`` attribute ``is_active``)

For the ``/scim/v2/Groups/.search`` endpoint, it is only possible to filter on ``displayName``, which filters by the ``name``
attribute of ``AuthorizationProfile``.

.. note::
    The POST, PUT and DELETE operations have been disabled for the ``/scim/v2/Groups`` endpoint.
    This is because the *content* of the authorization profiles is managed from the ZAC application. This means that
    roles, blueprint permissions and atomic permissions are NOT exposed through the SCIM interface.
