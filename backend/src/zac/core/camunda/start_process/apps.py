from django.apps import AppConfig


class StartProcessConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "zac.core.camunda.start_process"

    def ready(self):
        from .serializers import get_zaak_start_process_form_context
