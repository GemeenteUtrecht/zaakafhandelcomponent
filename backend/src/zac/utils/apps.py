from django.apps import AppConfig

from .oas_cache import replace_cache


class UtilsConfig(AppConfig):
    name = "zac.utils"

    def ready(self):
        from . import checks  # noqa

        replace_cache()
