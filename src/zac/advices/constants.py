from django.utils.translation import gettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices


class AdviceObjectTypes(DjangoChoices):
    zaak = ChoiceItem("zaak", _("Zaak"))
    document = ChoiceItem("document", _("Zaak"))
