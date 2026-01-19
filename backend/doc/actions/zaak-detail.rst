.. _zaak-detail-actions:

Zaak informatie
---------------

Manages ``ZAAK`` attributes as well as ``ZAAKEIGENSCHAP``pen. 
A ``ZAAKEIGENSCHAP`` can have a dropdown menu associated with its ``EIGENSCHAP``. The dropdown menu values are determined by :ref:`zaaktype attributes <ZaakTypeAttribute>`.
Editing a ``ZAAKEIGENSCHAP`` triggers validation done by the ZAC on the format of the value given by the user and the format as defined by the ``EIGENSCHAPSPECIFICATIE``.
Open Zaak does *not* validate this.

Betrokkenen
-----------

Manages related people. A ``ZAAK`` should always have a `behandelaar` and/or `initiator` (`hoofdbehandelaar`). An `initiator` will automatically be set to the user that created the ZAAK from within the ZAC.
Deleting or changing (basically a delete and create) a `(hoofd)behandelaar` will store the old `(hoofd)behandelaar` in the :ref:`oudbehandelaar <OudBehandelaren>` to keep track of who was the `(hoofd)behandelaar` during which dates.
Trying to delete a `(hoofd)behandelaar` will not be allowed if it is the only one. You can simply create a new `hoofdbehandelaar`, this will replace the current `hoofdbehandelaar`. 

Rechten
-------

Adding permissions is :class:`zac.accounts.models.Role`-based just like the :class:`zac.accounts.models.AuthorizationProfile`. You can assign a user :class:`zac.accounts.models.AtomicPermission` \s based on the selected :class:`zac.accounts.models.Role` and is limited by your own permissions. 
I.e., you can never grant a user more permissions than you have yourself.