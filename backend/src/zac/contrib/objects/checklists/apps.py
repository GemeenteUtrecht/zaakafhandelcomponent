from django.apps import AppConfig


class ChecklistsConfig(AppConfig):
    name = "zac.contrib.objects.checklists"

    def ready(self):
        from . import permissions  # noqa
