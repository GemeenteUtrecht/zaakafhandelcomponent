from django.apps import AppConfig


class ValidSignConfig(AppConfig):
    name = "zac.contrib.validsign"

    def ready(self):
        from zac.camunda.user_tasks import REGISTRY
        from zac.camunda.user_tasks.context import noop
        from zac.core.camunda import FORM_KEYS

        from .forms import ConfigurePackageForm, SignerFormSet

        FORM_KEYS.update(
            {
                "zac:validSign:configurePackage": {
                    "form": ConfigurePackageForm,
                    "formset": SignerFormSet,
                },
            }
        )

        REGISTRY["zac:validSign:configurePackage"] = noop
