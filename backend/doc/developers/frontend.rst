.. _frontend-configuration:

Frontend
========

The frontend is an Angular application generated using Nx (https://nx.dev) .


Installing dependencies
-----------------------

Install the NodeJS dependencies:

.. code-block:: bash

    $ npm i

Running the frontend
---------------------

The most easy way to start the (frontend) application is using docker-compose.

.. code-block:: bash

    % docker-compose up -d --build ingress-dev

Alternatively, if you want a to be able to modify backend files as well.

.. code-block:: bash

    $ docker-compose up -d --build ingress-dev-fullstack

The frontend might take several minutes to become available. Under certain conditions: the commands listed above might timeout the first time. In such cases re-running the command will likely solve the issue.
