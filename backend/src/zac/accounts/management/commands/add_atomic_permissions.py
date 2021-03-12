from django.core.management import BaseCommand

from zac.contrib.kownsl.api import get_review_requests
from zac.core.permissions import zaken_inzien
from zac.core.services import get_rollen_all, get_zaken_all

from ...constants import PermissionObjectType
from ...models import PermissionDefinition, User


class Command(BaseCommand):
    help = """
    Updating atomic permissions to read zaken.

    Note: this command only adds missing permissions, it doesn't remove them,
    since it's impossible to separate manually added permissions from ones created automatically.
    """

    def add_permission_to_user(self, user: User, zaak_url: str):
        if (
            not PermissionDefinition.objects.for_user(user)
            .actual()
            .filter(
                object_type=PermissionObjectType.zaak,
                object_url=zaak_url,
                permission=zaken_inzien.name,
            )
            .exists()
        ):
            permission_definition = PermissionDefinition.objects.create(
                object_type=PermissionObjectType.zaak,
                object_url=zaak_url,
                permission=zaken_inzien.name,
            )
            user.permission_definitions.add(permission_definition)

    def handle(self, **options):
        zac_usernames = list(
            User.objects.filter(is_active=True).values_list("username", flat=True)
        )

        # give access to zaak behandelaars
        rollen = get_rollen_all(
            betrokkeneType="medewerker", omschrijvingGeneriek="behandelaar"
        )
        zac_rollen = [
            rol
            for rol in rollen
            if (rol.betrokkene_identificatie or {}).get("identificatie", "")
            in zac_usernames
        ]
        for rol in zac_rollen:
            user = User.objects.get(
                username=rol.betrokkene_identificatie["identificatie"]
            )
            self.add_permission_to_user(user, rol.zaak)
        self.stdout.write("permissions for behandelaars are added")

        # give access to zaak reviewers
        for zaak in get_zaken_all():
            rr_usernames = [
                list(rr.user_deadlines.keys())
                for rr in get_review_requests(zaak)
                if rr.user_deadlines
            ]
            # flatten the list
            rr_usernames = sum(rr_usernames, [])
            rr_zac_uernames = list(set(rr_usernames) & set(zac_usernames))
            rr_zac_users = User.objects.filter(username__in=rr_zac_uernames)
            for user in rr_zac_users:
                self.add_permission_to_user(user, zaak.url)
        self.stdout.write("permissions for advisors are added")
