import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import get_template
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from zac.core.services import get_zaak
from zac.core.utils import build_absolute_url, get_ui_url

logger = logging.getLogger(__name__)


def send_email_to_requester(user, zaak_url, result, request=None, ui=False):
    if not user.email:
        logger.warning("Email to %s can't be sent - no known e-mail", user)
        return

    zaak = get_zaak(zaak_url=zaak_url)
    zaak_url = (
        get_ui_url(
            [settings.UI_ROOT_URL, "zaken", zaak.bronorganisatie, zaak.identificatie]
        )
        if ui
        else reverse(
            "core:zaak-detail",
            kwargs={
                "bronorganisatie": zaak.bronorganisatie,
                "identificatie": zaak.identificatie,
            },
        )
    )
    zaak.absolute_url = build_absolute_url(zaak_url, request)

    email_template = get_template("core/emails/access_result.txt")
    email_context = {
        "zaak": zaak,
        "result": result,
        "user": user,
    }

    message = email_template.render(email_context)
    send_mail(
        subject=_("Access Request to %(zaak)s") % {"zaak": zaak.identificatie},
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
