from django.apps import AppConfig


class CamundaConfig(AppConfig):
    name = "zac.camunda"

    def ready(self):
        from .dynamic_forms import context  # noqa
        from .user_tasks import redirects  # noqa
