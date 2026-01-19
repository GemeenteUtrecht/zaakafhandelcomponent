# Zaakafhandelcomponent

|          |                                                          |
|---------:|----------------------------------------------------------|
|   Versie | https://github.com/gemeenteutrecht/zaakafhandelcomponent/releases/latest|
|   Source | https://github.com/GemeenteUtrecht/zaakafhandelcomponent |
| Keywords | zaken, zaakgericht werken, GEMMA, Utrecht, Common Ground |
|   Python | 3.10                                                     |


Het zaakafhandelcomponent (ook wel: keteninzagecomponent) orchestreert het zaakgericht
werken binnen Gemeente Utrecht.
De backend koppelt met de Camunda proces-engine en overige API's in het Common Ground
landschap.
De frontend biedt de gebruikersinterface aan voor medewerkers, en communiceert met de
eigen backend.

## Documentatie

Voor configuratie, instellingen en algemene beheerdocumentatie: [![Documentation status](https://readthedocs.org/projects/zac-gu/badge/?version=latest)](https://zac-gu.readthedocs.io/nl/latest/?badge=latest)
Voor [API documentatie](https://zac.cg-intern.utrecht.nl/api/docs/).

## Projectstructuur

* De map [backend](backend) bevat het Django project wat de backend implementeert.
* De map [frontend](frontend) bevat de angular single-page app (SPA) die de user-interface
  implementeert.

## Developers

### Backend developers

Backend developers worden momenteel geacht zonder Docker te ontwikkelen (al zou het ook met docker kunnen).

Je hebt de volgende dependencies nodig op je development machine:

* PostgreSQL 10+
* Redis 5+ als je de aanbevolen cache engine gebruikt
* Python 3.10, met _virtualenv_ o.i.d.

Je hebt ook Elasticsearch nodig. Die kan worden gerund in Docker:

``` bash
docker-compose up -d elasticsearch
```

Zie de [backend](backend) folder voor verdere instructies.

### Frontend developers

Er zijn meerdere manieren waarop frontend developers kunnen ontwikkelen.

**Frontend dev server**

Run het volgende commando van binnen de `zaakafhandelcomponent/` om de development server te starten:

```bash
docker compose up -d --force-recreate --build ingress-dev
```

Dit zal zowel de backend (inclusief elasticsearch) en de frontend services starten.
Enige verandering aan de frontend source code zal de frontend herbouwen.

De gehele app is beschikbaar op `http://localhost:8080/` (en de UI is beschikbaar op `http://localhost:8080/ui`).

Om ervoor te zorgen dat alles werkt, zal de backend moeten worden geconfigureerd. Voor meer informatie hiervoor
kan worden verwezen naar de [backend readme](backend/readme.rst) of in the [readthedocs](https://zaakafhandelcomponent.readthedocs.io/en/latest/). In het kort:
- Een superuser moet aangemaakt worden.
- De services moeten worden toegevoegd: OpenZaak (Catalogi, Zaken, Besluiten, Documenten API), Kadaster, Kownsl, BPTL, DoWC, Object/Objecttypes API and notificaties API.
- Het camunda endpoint moeten worden geconfigureerd.
- De meta objecttypes moeten worden geconfigureerd.
- De zaken, objecten en documenten moeten worden geindexeerd in elasticsearch (met het management commando `python manage.py index_all`). Wellicht dat de cache eerst moet worden geleegd om problemen met gecache data te voorkomen.

```bash
$ python
>>> from django.core.cache import cache
>>> cache.clear()
```

**Aparte backend/frontend**

Developers die werken aan de frontend kunnen de backend services starten met Docker:

```bash
docker-compose up -d backend
```

De backend is vervolgens beschikbaar op `http://localhost:8000`.


### Full stack

Je kunt ook de full stack starten met docker-compose:

```bash
docker-compose up ingress
```

Componenten zijn dan beschikbaar op hun respectievelijke endpoints:

* Frontend/UI: `http://localhost:8080/ui/`
* API: `http://localhost:8080/api/`
* Django admin: `http://localhost:8080/admin/`


## Referenties

* [Issues](https://github.com/GemeenteUtrecht/zaakafhandelcomponent/issues)
* [Code](https://github.com/GemeenteUtrecht/zaakafhandelcomponent)

## Licentie

Copyright © VNG Realisatie 2019

Licensed under the [EUPL](LICENCE.md).
