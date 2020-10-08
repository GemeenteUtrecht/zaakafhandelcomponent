from django.apps import AppConfig
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from elasticsearch_dsl.connections import connections


class EsConfig(AppConfig):
    name = "zac.elasticsearch"
    verbose_name = _("Elasticsearch configuration")

    def ready(self):
        connections.configure(**settings.ELASTICSEARCH_DSL)

        # from django.utils.module_loading import autodiscover_modules
        # autodiscover_modules('documents')
