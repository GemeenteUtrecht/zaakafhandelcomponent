from django.utils.translation import gettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices


class ActivityStatuses(DjangoChoices):
    on_going = ChoiceItem("on_going", _("On-going"))
    finished = ChoiceItem("finished", _("Finished"))
