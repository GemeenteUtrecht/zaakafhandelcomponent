import logging
from typing import Tuple

from django.conf import settings
from django.core.management import BaseCommand

from zgw_consumers.concurrent import parallel

from zac.accounts.models import User

from ...models import ChecklistLock
from ..email import send_email_to_locker

logger = logging.getLogger(__name__)


def notify_user_of_unlock(user_zaak: Tuple[User, str]):
    send_email_to_locker(user=user_zaak[0], zaak_url=user_zaak[1])


def unlock_command() -> int:
    checklist_locks = ChecklistLock.objects.select_related("user").all()
    list_to_email = []
    for checklist_lock in checklist_locks:
        list_to_email.append((checklist_lock.user, checklist_lock.zaak))

    with parallel(max_workers=settings.MAX_WORKERS) as executor:
        list(executor.map(notify_user_of_unlock, list_to_email))

    ChecklistLock.objects.all().delete()

    return len(list_to_email)


class Command(BaseCommand):
    help = """
    Unlocks all locked checklists.

    """

    def handle(self, **options):
        count = unlock_command()
        logger.info("{count} checklists were unlocked.".format(count=count))
