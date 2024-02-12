from django.utils.translation import gettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices


class KownslTypes(DjangoChoices):
    advice = ChoiceItem("advice", _("Advice"))
    approval = ChoiceItem("approval", _("Approval"))


FORM_KEY_REVIEW_TYPE_MAPPING = {
    "zac:configureAdviceRequest": KownslTypes.advice,
    "zac:configureApprovalRequest": KownslTypes.approval,
}
