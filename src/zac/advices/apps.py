from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AdviceConfig(AppConfig):
    name = "zac.advices"
    verbose_name = _("advices")
