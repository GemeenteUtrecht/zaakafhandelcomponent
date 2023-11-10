from django.utils.translation import gettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices


class DocFileTypes(DjangoChoices):
    write = ChoiceItem("write", _("Write"))
    read = ChoiceItem("read", _("Read"))
    download = ChoiceItem("download", _("Download"))
