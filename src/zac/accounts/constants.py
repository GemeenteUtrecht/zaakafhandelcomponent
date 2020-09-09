from django.utils.translation import ugettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices


class AccessRequestResult(DjangoChoices):
    approve = ChoiceItem("approve", _("Approve"))
    reject = ChoiceItem("reject", _("Reject"))
    close = ChoiceItem("close", _("Close"))
