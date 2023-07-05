import logging
from typing import List

from django.core.management import BaseCommand

from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from zac.core.services import get_informatieobjecttypen_for_zaaktype, get_zaaktypen

from ...constants import PermissionObjectTypeChoices
from ...models import BlueprintPermission, Role

logger = logging.getLogger(__name__)


def generate_document_policies(zaaktype_policy: dict) -> List[dict]:
    zaaktype_omschrijving = zaaktype_policy.get("zaaktype_omschrijving")
    catalogus = zaaktype_policy.get("catalogus")

    if not zaaktype_omschrijving or not catalogus:
        return []

    # find zaaktype
    zaaktypen = get_zaaktypen(catalogus=catalogus, omschrijving=zaaktype_omschrijving)

    # find related iotypen
    document_policies = []
    for zaaktype in zaaktypen:
        if not zaaktype.informatieobjecttypen:
            continue

        iotypen = get_informatieobjecttypen_for_zaaktype(zaaktype)
        document_policies += [
            {
                "catalogus": iotype.catalogus,
                "iotype_omschrijving": iotype.omschrijving,
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            }
            for iotype in iotypen
        ]
    return document_policies


def add_blueprint_permissions_for_zaaktypen_and_iots():
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
    return added


class Command(BaseCommand):
    help = """
    Create blueprint permissions for all available zaaktypen and their
    related informatieobjecttypen.
    """

    def handle(self, **options):
        # give access to zaak behandelaars
        count = add_blueprint_permissions_for_zaaktypen_and_iots()
        logger.info(
            f" {count} blueprint permissions for zaak- and informatieobjecttypen are added"
        )
