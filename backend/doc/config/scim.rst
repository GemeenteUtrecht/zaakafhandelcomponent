.. _config-scim:

Access to the SCIM endpoints (N/A)
==================================

IMPLEMENTION ON HOLD AND CURRENTLY NOT AVAILABLE
The ZAC implements the :ref:`authorization_scim` for user provisioning. The endpoints
for this are themselves protected against unintended use.

To expose access to the SCIM endpoints, you should:

1. Navigate to the ZAC admin environment
2. Create a system user: **Accounts** > **Gebruikers** > **Gebruiker toevoegen**
3. Pick any username, as long as it won't conflict with a real human Active Directory
   username
4. Pick any (strong) password
5. Save the user by clicking **Opslaan en opnieuw bewerken**
6. Find the section **Rechten** > **Gebruikersrechten**. In the search box, search for
   "scim" and select the "Can use the SCIM endpoints" permission.
7. Save the user
8. Next, navigate to **Admin** > **Autorisatietoken** > **Tokens** and click
   **Token toevoegen**
9. Select the user that was created before and save the token

With the value of the token ("key"), the SCIM client can now make requests to the SCIM
endpoints, using the following header:

.. code-block:: none

    Authorization: Token <key>

Note that the "<" and ">" characters should not be present, e.g. a real token would look
like this:

.. code-block:: none

    Authorization: Token fe3f133828faec17036bbb0d2bed547321983bfd

The SCIM API root is available on the ``/scim/v2/`` URL, for example:
https://zac.cg-intern.utrecht.nl/scim/v2/.

.. _metaobjecttypesconfig: https://zac.cg-intern.utrecht.nl/admin/core/metaobjecttypesconfig/
.. _Kownsl: https://kownsl.cg-intern.utrecht.nl/api/v1/docs/
.. _DoWC: https://dowc.cg-intern.utrecht.nl/api/v1/docs/
.. _objects-and-objecttypes-api: https://objects-and-objecttypes-api.readthedocs.io/en/latest/api/index.html
