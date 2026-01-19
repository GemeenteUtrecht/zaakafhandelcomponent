from django.apps import AppConfig


class KownslConfig(AppConfig):
    name = "zac.contrib.objects.kownsl"

    def ready(self):
        from . import camunda  # noqa
        from . import permissions  # noqa
