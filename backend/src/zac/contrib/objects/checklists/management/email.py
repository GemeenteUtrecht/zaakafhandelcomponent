import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import get_template
from django.utils.translation import gettext_lazy as _

from furl import furl

from zac.core.services import get_zaak
from zac.core.utils import build_absolute_url

logger = logging.getLogger(__name__)


def send_email_to_locker(user, zaak_url):
    if not user.email:
        logger.warning("Email to %s can't be sent - no known e-mail", user)
        return

    zaak = get_zaak(zaak_url=zaak_url)
    zaak_url = furl(settings.UI_ROOT_URL)
    zaak_url.path.segments += [
        "zaken",
        zaak.bronorganisatie,
        zaak.identificatie,
    ]
    zaak.absolute_url = build_absolute_url(zaak_url.url)

    email_template = get_template("core/emails/unlock-checklists.txt")
    email_context = {
        "zaak": zaak,
        "user": user.get_full_name(),
    }

    message = email_template.render(email_context)
    send_mail(
        subject=_(
            "Notification: Checklist of zaak %(zaak)s was automatically unlocked."
        )
        % {"zaak": zaak.identificatie},
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
