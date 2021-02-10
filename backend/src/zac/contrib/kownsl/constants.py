from django.utils.translation import gettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices


class KownslTypes(DjangoChoices):
    advice = ChoiceItem("advice", _("Advies"))
    approval = ChoiceItem("approval", _("Accordering"))
