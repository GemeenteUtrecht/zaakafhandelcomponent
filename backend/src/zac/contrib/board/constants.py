from django.utils.translation import gettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices


class BoardObjectTypes(DjangoChoices):
    zaak = ChoiceItem("zaak", _("zaak"))
