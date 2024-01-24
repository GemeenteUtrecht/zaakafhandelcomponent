from django.utils.translation import gettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices


class ContezzaDocumentTypes(DjangoChoices):
    edit = ChoiceItem("edit", _("Edit"))
    resume = ChoiceItem("resume", _("Resume"))
    cancel = ChoiceItem("cancel", _("Cancel"))
    check_in = ChoiceItem("check_in", _("Check-in"))
