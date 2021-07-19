from django.apps import AppConfig


class ValidSignConfig(AppConfig):
    name = "zac.contrib.validsign"

    def ready(self):
        from zac.core.camunda import FORM_KEYS

        from . import camunda  # noqa

        FORM_KEYS.update({"zac:validSign:configurePackage": True})
