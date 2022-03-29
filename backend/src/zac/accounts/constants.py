from django.utils.translation import ugettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices


class AccessRequestResult(DjangoChoices):
    approve = ChoiceItem("approve", _("approved"))
    reject = ChoiceItem("reject", _("rejected"))


class PermissionObjectTypeChoices(DjangoChoices):
    zaak = ChoiceItem("zaak", _("zaak"))
    document = ChoiceItem("document", _("document"))


class PermissionReason(DjangoChoices):
    betrokkene = ChoiceItem("betrokkene", _("betrokkene"))
    toegang_verlenen = ChoiceItem("toegang verlenen", _("toegang verlenen"))
    activiteit = ChoiceItem("activiteit", _("activiteit"))
    adviseur = ChoiceItem("adviseur", _("adviseur"))
    accordeur = ChoiceItem("accordeur", _("accordeur"))
    checklist = ChoiceItem("checklist", _("checklist"))
