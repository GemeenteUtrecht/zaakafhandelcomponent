============
Installation
============

The project is developed in Python using the `Django framework`_. There are 3
sections below, focussing on developers, running the project using Docker and
hints for running the project in production.

.. _Django framework: https://www.djangoproject.com/


Development
===========


Prerequisites
-------------

You need the following libraries and/or programs:

* `Python`_ 3.9 or above
* Python `Virtualenv`_ and `Pip`_
* `PostgreSQL`_ 10 or above
* `Node.js`_
* `npm`_
* `Elasticsearch`_

.. _Python: https://www.python.org/
.. _Virtualenv: https://virtualenv.pypa.io/en/stable/
.. _Pip: https://packaging.python.org/tutorials/installing-packages/#ensure-pip-setuptools-and-wheel-are-up-to-date
.. _PostgreSQL: https://www.postgresql.org
.. _Node.js: http://nodejs.org/
.. _npm: https://www.npmjs.com/
.. _Elasticsearch: https://www.elastic.co/guide/en/elasticsearch/reference/7.9/install-elasticsearch.html


Getting started
---------------

Developers can follow the following steps to set up the project on their local
development machine.

1. Navigate to the location where you want to place your project.

2. Get the code:

   .. code-block:: bash

       $ git clone git@github.com:GemeenteUtrecht/zaakafhandelcomponent
       $ cd zac

3. Install all required libraries.

   .. code-block:: bash

       $ pip install -r requirements/dev.txt

4. Install the front-end CLI tool `gulp`_ if you've never installed them
   before and install the frontend libraries:

   .. code-block:: bash

       $ npm install -g gulp
       $ npm install
       $ gulp sass

5. Activate your virtual environment and create the database:

   .. code-block:: bash

       $ source env/bin/activate
       $ python src/manage.py migrate

6. Create a superuser to access the management interface:

   .. code-block:: bash

       $ python src/manage.py createsuperuser

7. You can now run your installation and point your browser to the address
   given by this command:

   .. code-block:: bash

       $ python src/manage.py runserver

**Note:** If you are making local, machine specific, changes, add them to
``src/zac/conf/local.py``. You can base this file on the
example file included in the same directory.

**Note:** You can run watch-tasks to compile `Sass`_ to CSS and `ECMA`_ to JS
using `gulp`_. By default this will compile the files if they change.

.. _ECMA: https://ecma-international.org/
.. _Sass: https://sass-lang.com/
.. _gulp: https://gulpjs.com/


Update installation
-------------------

When updating an existing installation:

1. Activate the virtual environment:

   .. code-block:: bash

       $ cd zac
       $ source env/bin/activate

2. Update the code and libraries:

   .. code-block:: bash

       $ git pull
       $ pip install -r requirements/dev.txt
       $ npm install
       $ gulp build

3. Update the database:

   .. code-block:: bash

       $ python src/manage.py migrate


Testsuite
---------

To run the test suite:

.. code-block:: bash

    $ python src/manage.py test zac


Docker
======

The easiest way to get the project started is by using `Docker Compose`_.

1. Clone or download the code from `Github`_ in a folder like
   ``zac``:

   .. code-block:: bash

       $ git clone git@github.com:gemeenteutrecht/zaakafhandelcomponent zac
       Cloning into 'zac'...
       ...

       $ cd zac

3. Set a secret key in the environment:

    .. code-block:: bash

        $ export SECRET_KEY=your_unique_key

    The key is a random string. You can generate it here: `https://www.miniwebtool.com/django-secret-key-generator/`_.

2. Start the database and web services:

   .. code-block:: bash

       $ docker-compose up -d
       Starting zac_db_1 ... done
       Starting zac_web_1 ... done

   It can take a while before everything is done. Even after starting the web
   container, the database might still be migrating. You can always check the
   status with:

   .. code-block:: bash

       $ docker logs -f zac_web_1

3. Create an admin user and load initial data. If different container names
   are shown above, use the container name ending with ``_web_1``:

   .. code-block:: bash

       $ docker exec -it zac_web_1 /app/src/manage.py createsuperuser
       Username: admin
       ...
       Superuser created successfully.

4. Point your browser to ``http://localhost:8000/`` to access the project's
   management interface with the credentials used in step 3.

   If you are using ``Docker Machine``, you need to point your browser to the
   Docker VM IP address. You can get the IP address by doing
   ``docker-machine ls`` and point your browser to
   ``http://<ip>:8000/`` instead (where the ``<ip>`` is shown below the URL
   column):

   .. code-block:: bash

       $ docker-machine ls
       NAME      ACTIVE   DRIVER       STATE     URL
       default   *        virtualbox   Running   tcp://<ip>:<port>

5. To shutdown the services, use ``docker-compose down`` and to clean up your
   system you can run ``docker system prune``.

.. _Docker Compose: https://docs.docker.com/compose/install/
.. _Github: https://github.com/gemeenteutrecht/zaakafhandelcomponent.git


More Docker
-----------

If you just want to run the project as a Docker container and connect to an
external database, you can build and run the ``Dockerfile`` and pass several
environment variables. See ``src/zac/conf/docker.py`` for
all settings.

.. code-block:: bash

    $ docker build . && docker run \
        -p 8000:8000 \
        -e DJANGO_SETTINGS_MODULE=zac.conf.docker \
        -e DATABASE_USERNAME=... \
        -e DATABASE_PASSWORD=... \
        -e DATABASE_HOST=... \
        --name zac

    $ docker exec -it zac /app/src/manage.py createsuperuser

Settings
========

All settings for the project can be found in
``src/zac/conf``.
The file ``local.py`` overwrites settings from the base configuration.

Generating the API spec
=======================

Installation of ``zds-schema`` makes the binary ``generate_schema`` available,
which generates the ``src/openapi.yaml`` using drf-spectacular.

Make sure you have installed the ``npm`` dependencies before using this.

Commands
========

Commands can be executed using:

.. code-block:: bash

    $ python src/manage.py <command>

There are no specific commands for the project. See
`Django framework commands`_ for all default commands, or type
``python src/manage.py --help``.

.. _Django framework commands: https://docs.djangoproject.com/en/dev/ref/django-admin/#available-commands
