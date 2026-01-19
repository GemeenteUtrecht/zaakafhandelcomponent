from django.apps import AppConfig
from django.core.cache import caches
from django.core.signals import request_finished
from django.utils.translation import gettext_lazy as _


class CoreConfig(AppConfig):
    name = "zac.core"
    verbose_name = _("zaakafhandelcomponent")

    def ready(self):
        from . import blueprints  # noqa
        from .camunda.select_documents import context  # noqa
        from .camunda.zet_resultaat import context  # noqa

        request_finished.connect(clear_request_cache)

        # Patch zgw-consumers Service model for backward compatibility with 1.x
        from zgw_consumers.client import build_client as _build_client
        from zgw_consumers.models import Service

        from zac.zgw_client import ZGWClient

        def build_client(self, **kwargs):
            """
            Build a ZGWClient for this Service.

            Provides backward compatibility with zgw-consumers <1.0 by using
            our custom ZGWClient instead of the default client.
            """
            return _build_client(self, client_factory=ZGWClient, **kwargs)

        Service.build_client = build_client


def clear_request_cache(sender, **kwargs):
    cache = caches["request"]
    cache.clear()
