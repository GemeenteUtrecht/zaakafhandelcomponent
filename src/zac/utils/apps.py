from django.apps import AppConfig


class UtilsConfig(AppConfig):
    name = 'zac.utils'

    def ready(self):
        from . import checks  # noqa
