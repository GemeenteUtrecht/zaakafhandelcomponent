from django.apps import AppConfig


class ChecklistsConfig(AppConfig):
    name = "zac.objects.checklists"

    def ready(self):
        from . import permissions  # noqa
