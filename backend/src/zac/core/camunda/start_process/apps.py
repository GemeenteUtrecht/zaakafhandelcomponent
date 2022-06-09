from django.apps import AppConfig


class StartProcessConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "zac.core.camunda.start_process"

    def ready(self):
        from zac.core.camunda.utils import FORM_KEYS

        FORM_KEYS.update(
            {
                "zac:StartProcessForm": True,
            }
        )
