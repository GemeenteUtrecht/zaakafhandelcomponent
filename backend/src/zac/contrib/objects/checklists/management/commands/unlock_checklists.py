import logging
from copy import deepcopy
from typing import Dict, List, Tuple

from django.conf import settings
from django.core.management import BaseCommand

from zgw_consumers.concurrent import parallel

from zac.accounts.models import User
from zac.contrib.objects.services import fetch_all_locked_checklists
from zac.core.services import update_object_record_data

from ..email import send_email_to_locker

logger = logging.getLogger(__name__)


def unlock_checklists(checklists: List[Dict]):
    def _unlock_checklists(checklist_obj: Dict):
        checklist_obj["record"]["data"]["lockedBy"] = None
        update_object_record_data(
            object=checklist_obj,
            data=checklist_obj["record"]["data"],
        )

    with parallel(max_workers=settings.MAX_WORKERS) as executor:
        executor.map(_unlock_checklists, checklists)


def notify_user_of_unlock(user_zaak: Tuple[User, str]):
    send_email_to_locker(user=user_zaak[0], zaak_url=user_zaak[1])


def unlock_command() -> int:
    checklists = fetch_all_locked_checklists()
    unlock_checklists(deepcopy(checklists))
    checklist_lockers = [obj["record"]["data"]["lockedBy"] for obj in checklists]
    users = User.objects.filter(username__in=checklist_lockers).in_bulk(
        field_name="username"
    )
    list_to_email = []
    for checklist in checklists:
        locker = checklist["record"]["data"]["lockedBy"]
        user = users.get(locker, None)
        if not user:
            logger.warning("User %s can't be found.", locker)
            continue

        list_to_email.append((user, checklist["record"]["data"]["zaak"]))

    with parallel(max_workers=settings.MAX_WORKERS) as executor:
        list(executor.map(notify_user_of_unlock, list_to_email))

    return len(list_to_email)


class Command(BaseCommand):
    help = """
    Unlocks all locked checklists.

    """

    def handle(self, **options):
        count = unlock_command()
        logger.info("{count} checklists were unlocked.".format(count=count))
