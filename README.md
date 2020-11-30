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
