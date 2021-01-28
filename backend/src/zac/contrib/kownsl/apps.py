from django.apps import AppConfig


class KownslConfig(AppConfig):
    name = "zac.contrib.kownsl"

    def ready(self):
        #  register the user task context
        from . import camunda  # noqa
