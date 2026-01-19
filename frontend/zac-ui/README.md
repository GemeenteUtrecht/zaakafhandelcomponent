# ZAC-ui

ZAC-ui is de gebruikersinterface van de applicatie ZAC: Zaakafhandelcomponent. Deze applicatie stelt de gebruiker in staat om te werken met zaakgegevens en processen te beheren.

## Documentatie

Dit project is gegenereerd met behulp van [Nx](https://nx.dev).

🔎 **Nx is a set of Extensible Dev Tools for Monorepos.**

[Nx Documentation](https://nx.dev/angular)

## Algemene setup

Dit project bevat de applicatie [zac-ui](apps/zac-ui) in [apps/](apps), die meerdere libraries uit [libs/](libs) gebruikt.

## Application

De enige applicatie in dit project is momenteel `apps/zac-ui`. Deze toepassingen dienen als een omhulsel voor de functies en handelen de routing af.

## Library

In de `libs/` directory vind je alle `features` en `shared` modules. Deze libraries moeten worden gegenereerd onder bepaalde voorwaarden. Gebruik het onderstaande formaat met de relevante parameters om een compatibele library te genereren.

`ng generate @nrwl/angular:library --name=$feature-name --style=scss --directory=features --importPath=@gu/$feature-name --prefix=gu --publishable --no-interactive`

Op deze manier zijn de libraries deelbaar over andere `libs` en `apps`. Ze kunnen worden geïmporteerd vanuit `@gu/$feature-name`.

## Development server

Run `npm install`

Dit project moet worden uitgevoerd met behulp van `docker-compose` zoals beschreven in de root [README](../../README.md). Alleen het uitvoeren van dit front-end project staat je niet toe om toegang te krijgen tot de juiste API's, aangezien de authenticatie wordt beheerd door de omhullende Django applicatie.

