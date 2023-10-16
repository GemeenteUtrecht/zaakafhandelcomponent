.. _zaak-detail-actions:

Zaak informatie
---------------

Manages ZAAK attributes as well as ZAAKEIGENSCHAPs. 
A ZAAKEIGENSCHAP can have a dropdown menu associated with its EIGENSCHAP. The dropdown menu values are determined by :ref:`zaaktype attributes <ZaakTypeAttribute>`.
Editing a ZAAKEIGENSCHAP triggers validation done by the ZAC on the format of the value given by the user and the format as defined by the EIGENSCHAPSPECIFICATIE.
Open Zaak does *not* validate this.

Betrokkenen
-----------

Manages related people. A ZAAK will always require a `behandelaar` or `initiator`.