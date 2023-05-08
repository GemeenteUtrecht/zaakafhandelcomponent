from django.core.management import BaseCommand

from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from zac.accounts.api.serializers import generate_document_policies
from zac.core.services import get_zaaktypen

from ...constants import PermissionObjectTypeChoices
from ...models import BlueprintPermission, Role


class Command(BaseCommand):
    help = """
    Create blueprint permissions for all available zaaktypen and their
    related informatieobjecttypen.
    """

    def handle(self, **options):
        # give access to zaak behandelaars
        zaaktypen = get_zaaktypen()
        roles = Role.objects.all()
        added = 0
        for zaaktype in zaaktypen:
            policy = {
                "catalogus": zaaktype.catalogus,
                "zaaktype_omschrijving": zaaktype.omschrijving,
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            }
            document_policies = generate_document_policies(policy)
            for role in roles:
                obj, created = BlueprintPermission.objects.get_or_create(
                    role=role,
                    policy=policy,
                    object_type=PermissionObjectTypeChoices.zaak,
                )
                if created:
                    added += 1

                for policy in document_policies:
                    permission, created = BlueprintPermission.objects.get_or_create(
                        role=role,
                        object_type=PermissionObjectTypeChoices.document,
                        policy=policy,
                    )
                    if created:
                        added += 1
        self.stdout.write(f" {added} blueprint permissions for zaaktypen are added")
