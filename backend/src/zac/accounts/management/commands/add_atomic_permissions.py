from django.core.management import BaseCommand

from zac.contrib.kownsl.api import get_review_requests
from zac.core.services import get_rollen_all, get_zaken_all

from ...permission_loaders import (
    add_permission_for_behandelaar,
    add_permissions_for_advisors,
)


class Command(BaseCommand):
    help = """
    Updating atomic permissions to read zaken.

    Note: this command only adds missing permissions, it doesn't remove them,
    since it's impossible to separate manually added permissions from ones created automatically.
    """

    def handle(self, **options):
        # give access to zaak behandelaars
        rollen = get_rollen_all(
            betrokkeneType="medewerker", omschrijvingGeneriek="behandelaar"
        )
        for rol in rollen:
            add_permission_for_behandelaar(rol)
        self.stdout.write("permissions for behandelaars are added")

        # give access to zaak reviewers
        for zaak in get_zaken_all():
            for review_request in get_review_requests(zaak):
                add_permissions_for_advisors(review_request)
        self.stdout.write("permissions for advisors are added")
