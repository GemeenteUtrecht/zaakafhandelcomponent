from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AdviceConfig(AppConfig):
    name = "zac.advices"
    verbose_name = _("advices")

    def ready(self):
        register_form_keys()


def register_form_keys():
    from zac.core.camunda import FORM_KEYS

    from .forms import AdviceForm, UploadDocumentFormset

    FORM_KEYS.update(
        {"zac:getAdvice": {"form": AdviceForm, "formset": UploadDocumentFormset}}
    )
