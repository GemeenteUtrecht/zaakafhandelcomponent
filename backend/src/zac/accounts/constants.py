from django.utils.translation import ugettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices


class AccessRequestResult(DjangoChoices):
    approve = ChoiceItem("approve", _("approved"))
    reject = ChoiceItem("reject", _("rejected"))


class PermissionObjectType(DjangoChoices):
    zaak = ChoiceItem("zaak", _("zaak"))
    document = ChoiceItem("document", _("document"))
