from django.apps import AppConfig


class ActivitiesConfig(AppConfig):
    name = "zac.activities"

    def ready(self):
        from . import permissions  # noqa
