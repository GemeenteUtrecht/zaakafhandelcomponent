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
            for permission in permissions:
                if not BlueprintPermission.objects.filter(
                    permission=permission,
                    policy__zaaktype_omschrijving=zaaktype.omschrijving,
                    policy__catalogus=zaaktype.catalogus,
                ).exists():
                    obj = BlueprintPermission.objects.create(
                        permission=permission,
                        policy={
                            "catalogus": zaaktype.catalogus,
                            "zaaktype_omschrijving": zaaktype.omschrijving,
                            "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
                        },
                        object_type=PermissionObjectType.zaak,
                    )
                    added.append(obj)

        self.stdout.write(
            f" {len(added)} blueprint permissions for zaaktypen are added"
        )
