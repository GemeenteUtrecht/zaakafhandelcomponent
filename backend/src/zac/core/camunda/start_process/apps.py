from django.apps import AppConfig


class StartProcessConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "zac.core.camunda.start_process"

    def ready(self):
        pass
