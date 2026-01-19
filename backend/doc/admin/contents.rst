.. _admin-panel-contents:

Contents
========

Although the :class:`.ApplicationGroup` and their content is quite dynamic, we will quickly dive into the most important subpanels.

Accounts
--------

On this page admins can manage :class:`.User` accounts and permission related data.

Access requests
~~~~~~~~~~~~~~~

:class:`.AccessRequest`: related to :class:`.User`. **Access requests** can be requested by a **user** and must be approved
by a handler that has at least the requested permissions to the requested object.

ApplicationToken authorizations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:class:`.ApplicationToken`: an **application token** can be generated and given appropriate permissions so that application consumers can request information.

ApplicationToken authorization profiles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:class:`.ApplicationTokenAuthorizationProfile`: used to relate an :class:`.ApplicationToken` to an :class:`.AuthorizationProfile`.

Atomic permissions
~~~~~~~~~~~~~~~~~~

:class:`.AtomicPermission`: related to :class:`.User`. **Atomic permissions** can be given to a user to grant
them specific access to specific objects.


Blueprint permissions
~~~~~~~~~~~~~~~~~~~~~

:class:`.BlueprintPermission`: related to :class:`.Role`. **Blueprint permissions** pertain to the objects:

  * `zaak`,
  * `document`.
  
They hold policies that specify:

  * CATALOGUS, 
  * INFORMATIEOBJECTTYPE/ZAAKTYPE,
  * maximum confidentiality level.

Users
~~~~~

:class:`.User`: **users** should be automatically generated when they try to login through SSO.

Groups
~~~~~~

:class:`.Group`: related to :class:`.User`. **Groups** can host multiple **users** and **users** can be part of multiple **groups**.

Roles
~~~~~

:class:`.Role`: holds a set of :class:`.BlueprintPermission`.

Tokens
~~~~~~

:class:`.Token`: a token generated for a specific :class:`.User`. Should not normally be used, rather use the :class:`.ApplicationToken`.

User authorization profiles
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:class:`.UserAuthorizationProfile`: used to relate a :class:`.User` to a specific :class:`.AuthorizationProfile`.

Activities
----------

Activities
~~~~~~~~~~

:class:`.Activity`: ad-hoc activities can be created in a ZAAK and are tasks that are not part of the business process.
Activities can be assigned to :class:`.User` or :class:`.Group`.

Events
~~~~~~

:class:`.Event`: a notable log-worthy event pertaining to a specific :class:`.Activity`.

Admin index
-----------

Application groups
~~~~~~~~~~~~~~~~~~

:class:`.ApplicationGroup`: used to manage the appearance of the admin panel.

Axes
----

Access attempts
~~~~~~~~~~~~~~~

:class:`.AccessAttempt`: manage failed access attempts to the ZAC. Here you can clear the attempts if users are locked out.

Access logs
~~~~~~~~~~~

:class:`.AccessLog`: monitor failed access attempts.

Boards
------

Boards
~~~~~~

:class:`.Board`: manage boards, AKA dashboards. Boards hold :class:`.BoardColumn` s.
Board columns hold board items, which currently hold ZAAK or OBJECT URL-references.

Board columns
~~~~~~~~~~~~~

:class:`.BoardColumn`: manage board columns. Related to :class:`.Board`. A board column holds :class:`.BoardItem`.

Board items
~~~~~~~~~~~

:class:`.BoardItem`: manage board items. Related to :class:`.BoardColumn`.

Camunda
-------

Camunda configuration
~~~~~~~~~~~~~~~~~~~~~

:class:`.CamundaConfig`: manage camunda configuration. Here you can configure the required credentials to connect with Camunda.

Camunda tasks
~~~~~~~~~~~~~

:class:`.KillableTask`: manage which camunda tasks are killable and which aren't. I.e., can be cancelled by users.

Checklist
---------

Checklist locks
~~~~~~~~~~~~~~~

:class:`.ChecklistLock`: manage checklist locking to prevent data loss caused by concurrent editing of a checklist.

Elasticsearch configuration
---------------------------

Search reports
~~~~~~~~~~~~~~

:class:`.SearchReport`: manage saved search queries related to elasticsearch. A search report can be used to quickly requery complex searches. These are not results but merely the query.

Notifications
-------------

Registed subscriptions
~~~~~~~~~~~~~~~~~~~~~~

:class:`.Subscription`: manage subscriptions to Open Notificaties channel subscriptions. Used to automatically set the required notifications.

Organisatieonderdelen
---------------------

:class:`.OrganisatieOnderdeel`: manage "organisatieonderdelen". Not currently used.

Websites
--------

Websites
~~~~~~~~

:class:`.Site`: manage host site. There should be only one row and its domain should point to public URL of application.

Zaakafhandelcomponent
---------------------

BRP configuration
~~~~~~~~~~~~~~~~~

:class:`.BRPConfig`: manage which :class:`.Service` points to the BRP.

DoWC configuration
~~~~~~~~~~~~~~~~~

:class:`.DowcConfig`: manage which :class:`.Service` points to the DoWC.

Forms configuration
~~~~~~~~~~~~~~~~~~~

:class:`.FormsConfig`: manage which :class:`.Service` points to the Open Forms. Not currently used.

Global configuration
~~~~~~~~~~~~~~~~~~~~

:class:`.CoreConfig`: manage the core configuration of the ZAC. In here you configure the primary services, authorization ID of the BPTL and whether or not you allow non-SSO login.
The names of the fields are designed to be self-explanatory.

Kadaster configuration
~~~~~~~~~~~~~~~~~~~~~~

:class:`.KadasterConfig`: manage which :class:`.Service` points to the `Kadaster`. Also configures the `locatieserver` to be used.

Kownsl configuration
~~~~~~~~~~~~~~~~~~~~

:class:`.KownslConfig`: manage which :class:`.Service` points to the Kownsl.

Meta objecttype configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:class:`.MetaObjectTypesConfig`: manage the URL-references of `meta` objecttypes. The fields and the dropdown values are designed to be self self-explanatory.
Required for checklist functionality, storing historic ZAAK `behandelaren`, providing basic information to kick start business processes in camunda and 
dropdown values for ZAAKEIGENSCHAPpen.

ZGW consumers
-------------

NLX configuration
~~~~~~~~~~~~~~~~~

:class:`.NLXConfig`: manage NLX configuration. Not currently used.

Services
~~~~~~~~

:class:`.Service`: manage services. Please refer to :ref:`config` for instructions.

Landing
-------

Landing page configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~

:class:`.LandingPageConfiguration`: manage landing page configuration. This is where you construct the sections, titles, links and images of the landing page.

Mozilla django oidc db
----------------------

:class:`.OpenIDConnectConfig`: manage OIDC/SSO configuration. Supercedes ADFS configuration.