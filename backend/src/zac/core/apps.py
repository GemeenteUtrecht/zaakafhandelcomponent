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

        # Patch zgw-consumers Document model for zgw-consumers 1.x compatibility
        # Fix broken get_vertrouwelijkheidaanduiding_display method
        from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
        from zgw_consumers.api_models.documenten import Document

        def _fixed_get_vertrouwelijkheidaanduiding_display(self):
            """Fixed version that works with zgw-consumers 1.x where values is a list."""
            # In Django choices, use the choices tuple to look up the label
            for choice_value, choice_label in VertrouwelijkheidsAanduidingen.choices:
                if choice_value == self.vertrouwelijkheidaanduiding:
                    return choice_label
            return self.vertrouwelijkheidaanduiding

        Document.get_vertrouwelijkheidaanduiding_display = (
            _fixed_get_vertrouwelijkheidaanduiding_display
        )


def clear_request_cache(sender, **kwargs):
    cache = caches["request"]
    cache.clear()
