from django.apps import AppConfig


class ValidSignConfig(AppConfig):
    name = "zac.contrib.validsign"

    def ready(self):
        from zac.core.camunda import FORM_KEYS

        from .forms import ConfigurePackageForm

        FORM_KEYS.update(
            {"zac:validsign:configurePackage": {"form": ConfigurePackageForm},}
        )
