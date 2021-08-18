from django.apps import AppConfig
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from elasticsearch_dsl.connections import connections


class EsConfig(AppConfig):
    name = "zac.elasticsearch"
    verbose_name = _("Elasticsearch configuration")

    def ready(self):
        from . import blueprints  # noqa

        connections.configure(**settings.ELASTICSEARCH_DSL)
