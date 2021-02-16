from django.apps import AppConfig
from django.core.cache import caches
from django.core.signals import request_finished
from django.utils.translation import gettext_lazy as _


class CoreConfig(AppConfig):
    name = "zac.core"
    verbose_name = _("zaakafhandelcomponent")

    def ready(self):
        from .camunda.select_documents import context  # noqa

        request_finished.connect(clear_request_cache)


def clear_request_cache(sender, **kwargs):
    cache = caches["request"]
    cache.clear()
