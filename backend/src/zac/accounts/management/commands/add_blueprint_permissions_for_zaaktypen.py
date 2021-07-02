from django.core.management import BaseCommand

from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from zac.accounts.permissions import registry
from zac.core.blueprints import ZaakTypeBlueprint
from zac.core.services import get_zaaktypen

from ...constants import PermissionObjectType
from ...models import BlueprintPermission


class Command(BaseCommand):
    help = """
    Create blueprint permissions for all available zaaktypen
    """

    def handle(self, **options):
        # give access to zaak behandelaars
        zaaktypen = get_zaaktypen()
        permissions = [
            name
            for name, perm in registry.items()
            if isinstance(perm.blueprint_class(), ZaakTypeBlueprint)
        ]
        added = []
        for zaaktype in zaaktypen:
            policy = {
                "catalogus": zaaktype.catalogus,
                "zaaktype_omschrijving": zaaktype.omschrijving,
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            }

            for permission in permissions:
                obj, created = BlueprintPermission.objects.get_or_create(
                    permission=permission,
                    policy=policy,
                    object_type=PermissionObjectType.zaak,
                )
                if created:
                    added.append(obj)

        self.stdout.write(
            f" {len(added)} blueprint permissions for zaaktypen are added"
        )
