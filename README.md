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
* Python 3.7, with virtualenv recommended or similar tools

You also need Elastic Search, but that one can easily be run using Docker:

```bash
docker-compose up -d elasticsearch
```

See the `backend` folder for further instructions.

### Frontend developers

Developers working on the frontend can bring up the backend services using Docker:

```bash
docker-compose up -d backend
```

This will expose the backend on `http://localhost:8000`.

Future improvements could bring in a database fixture with out-of-the-box configuration.
Alternatively, you could develop against `https://zac-test.utrechtproeftuin.nl` as
backend.

### Full stack

You can bring up the full stack of backend + frontend and supporting services using
docker-compose:

```bash
docker-compose up
```

Components are then available on their respective paths:

* Frontend/UI: http://localhost:8080/ui/
* API: http://localhost:8080/api/
* Django admin: http://localhost:8080/admin/
