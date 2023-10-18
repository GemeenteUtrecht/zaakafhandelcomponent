.. _backend-configuration:

Backend
=======

Dependencies
------------

To run the backend, create a Python virtual environment and install the dependencies:

.. code-block:: bash

    $ virtualenv env -p /usr/bin/python3.9  # create the virtualenv if it doesn't exist
    $ source env/bin/activate  # activate the virtualenv
    (env)$ pip install -r requirements/dev.txt  # install the dependencies

Database
--------

Make sure you have a PostgreSQL database prepared. The default name/credentials are in
``src/zac/conf/dev.py``:

.. code-block:: bash

    $ createuser zac -d -P
    $ createdb zac -U zac

Next, migrate to create all the tables (or update to the newer version of database
schema):

.. code-block:: bash

    (env)$ python src/manage.py migrate

And create a super-user for development (only required for first time set-up):

.. code-block:: bash

    (env)$ python src/manage.py createsuperuser

Start development server
------------------------

Run the dev server:

.. code-block:: bash

    (env)$ python src/manage.py runserver


Configuration
-------------

The ZAC requires some initial configuration before you can start using it. Open the
admin interface at ``http://localhost:8000/admin/`` and log in with your super-user
credentials.

See the :ref:`config` documentation to configure the runtime parameters. You can
use NLX if you have an outway running on your machine.

Elastic Search
--------------

Elasticsearch is for performance reasons the dominant read-only database for many different features
mostly related to filtering based on some EIGENSCHAP value or OBJECT value, etc. The ZAC requires
Elastic Search 7.9 to function. You can either run ES on the host machine or make use of the docker-compose service:

.. code-block:: bash

    docker-compose up -d elasticsearch

Give the service some time to come up.

Now, with all the services correctly configured and ES running, you can index the ZAAKs, OBJECTs and INFORMATIEOBJECTs:

.. code-block:: bash

    (env)$ python src/manage.py index_all

Indexing takes some time. You can see how far along it is in the logs.

Note that your dev-environment does not receive notifications (callbacks) from Open Notifications if they are sent 
so refreshing the zaken list will not reflect the up-to-date state. Reindex when required.
