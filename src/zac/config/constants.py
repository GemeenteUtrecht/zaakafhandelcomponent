from django.utils.translation import ugettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices


class APITypes(DjangoChoices):
    zrc = ChoiceItem('zrc', _("ZRC"))
    ztc = ChoiceItem('ztc', _("ZTC"))
    drc = ChoiceItem('drc', _("DRC"))
    brc = ChoiceItem('brc', _("BRC"))
