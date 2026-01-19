from django.utils.translation import gettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices


class KownslTypes(DjangoChoices):
    advice = ChoiceItem("advice", _("Advice"))
    approval = ChoiceItem("approval", _("Approval"))


class KownslStatus(DjangoChoices):
    approved = ChoiceItem("approved", _("Approved"))
    not_approved = ChoiceItem("not_approved", _("Not approved"))
    pending = ChoiceItem("pending", _("Pending"))
    canceled = ChoiceItem("canceled", _("Canceled"))
    completed = ChoiceItem("completed", _("Completed"))


FORM_KEY_REVIEW_TYPE_MAPPING = {
    "zac:configureAdviceRequest": KownslTypes.advice,
    "zac:configureApprovalRequest": KownslTypes.approval,
}
