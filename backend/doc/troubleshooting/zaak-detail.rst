.. _zaak-detail-troubleshooting:

Zaak detail
===========

Zaak detail page does not load
------------------------------

* Make sure user has permissions. Please refer to :ref:`authorizations <authorizations-index>`.
* Make sure `meta` objecttypes are set correctly in :ref:`admin panel <admin-panel>`. Please refer to :ref:`config-metaobjecttypes`.

Zaak detail page data out of sync
---------------------------------

* Clear cache: `clear cache`_. ADVICE: it's easiest to clear all cache patterns with `{'pattern': '*'}` if running redis as caching backend.
* Reindex zaak: `reindex-zaak`_. !WARNING: do NOT set `reset_indices: True` or suffer the consequences!

Cannot change `betrokkenen`
----------------------------

* Make sure the ZAC can connect to Open Zaak.
* Make sure Open Zaak and Open Notificaties can communicate with each other.
* Make sure the ZAC is subscribed and can receive notifications from Open Notificaties.
* Make sure there is at least one `(hoofd)behandelaar`.
* Make sure you have the correct permissions. Please refer to :ref:`authorizations <authorizations-index>`.

.. _clear cache: https://zac.cg-intern.utrecht.nl/api/docs/#tag/management/operation/core_management_cache_reset_create
.. _reindex zaak: https://zac.cg-intern.ont.utrecht.nl/api/docs/#tag/management/operation/search_management_reindex_zaak_create