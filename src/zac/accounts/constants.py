from django.utils.translation import ugettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices


class RequestAccessResult(DjangoChoices):
    approve = ChoiceItem("approve", _("Approve"))
    reject = ChoiceItem("reject", _("Reject"))
