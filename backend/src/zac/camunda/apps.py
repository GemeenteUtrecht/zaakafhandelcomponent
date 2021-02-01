from django.apps import AppConfig


class CamundaConfig(AppConfig):
    name = "zac.camunda"

    def ready(self):
        from .user_tasks import redirects  # noqa
