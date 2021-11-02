# Zaakafhandelcomponent

Het zaakafhandelcomponent (ook wel: keteninzagecomponent) orchestreert het zaakgericht
werken binnen Gemeente Utrecht.

De backend koppelt met de Camunda proces-engine en overige API's in het Common Ground
landschap.

De frontend biedt de gebruikersinterface aan voor medewerkers, en communiceert met de
eigen backend.

## Projectstructuur

* De map `backend` bevat het Django project wat de backend implementeert.
* De map `frontend` bevat de angular single-page app (SPA) die de user-interface
  implementeert.

## Developers

### Backend developers

Backend developers are currently expected to develop without Docker (although it's not
impossible).

You need the following dependencies on your development machine:

* PostgreSQL 10+
* Redis 5+ if you're using the real cache backend, which is recommended
* Python 3.9, with virtualenv recommended or similar tools

You also need Elastic Search, but that one can easily be run using Docker:

```bash
docker-compose up -d elasticsearch
```

See the `backend` folder for further instructions.

### Frontend developers

There are multiple ways to work on the frontend.

**Frontend dev server**

From inside the `zaakafhandelcomponent/` run the following command to
start the development server:

```bash
docker-compose up -d ingress-dev
```

This brings up both the backend (including the elasticsearch service) and the frontend.
Any change to the frontend source code will cause the frontend to be rebuilt.

The entire app is available on `http://localhost:8080` (and the new UI is available at `http://localhost:8080/ui`.

For everything to work properly, the backend needs to be configured. More information on this can be found in the
backend README. But, as a checklist:
- A superuser needs to be created
- The services to be added for OpenZaak (Catalogi, Zaken, Besluiten, Documenten API), Kadaster, Kownsl, Open Forms, Object/Objecttypes API and notificaties API.
- The Camunda endpoint needs to be specified.
- The kadaster configuration needs to point to the Kadaster Service created.
- The Zaken need to be indexed in elastic (with the management command `python manage.py index_zaken`). In case of problems, it can help to clear the django cache in the docker container:
```
$ python
>>> from django.core.cache import cache
>>> cache.clear()
```

**Separate backend/frontend**

Developers working on the frontend can bring up the backend services using Docker:

```bash
docker-compose up -d backend
```

This will expose the backend on `http://localhost:8000`.


### Full stack

You can bring up the full stack of backend + frontend and supporting services using
docker-compose:

```bash
docker-compose up ingress
```

Components are then available on their respective paths:

* Frontend/UI: http://localhost:8080/ui/
* API: http://localhost:8080/api/
* Django admin: http://localhost:8080/admin/
