import logging
from typing import List

from django.core.management import BaseCommand

from zgw_consumers.api_models.catalogi import Catalogus
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from zac.core.services import (
    fetch_catalogus,
    get_informatieobjecttypen_for_zaaktype,
    get_zaaktypen,
)

from ...constants import PermissionObjectTypeChoices
from ...models import BlueprintPermission, Role

logger = logging.getLogger(__name__)


def generate_document_policies(
    zaaktype_policy: dict,
    catalogus: Catalogus,
    va: str,
) -> List[dict]:
    zaaktype_omschrijving = zaaktype_policy.get("zaaktype_omschrijving")
    if not zaaktype_omschrijving or not catalogus:
        return []

    # find zaaktype
    zaaktypen = get_zaaktypen(
        catalogus=catalogus.url, omschrijving=zaaktype_omschrijving
    )

    # find related iotypen
    document_policies = []
    for zaaktype in zaaktypen:
        if not zaaktype.informatieobjecttypen:
            continue

        iotypen = get_informatieobjecttypen_for_zaaktype(zaaktype)
        document_policies += [
            {
                "catalogus": catalogus.domein,
                "iotype_omschrijving": iotype.omschrijving,
                "max_va": va[0],
            }
            for iotype in iotypen
        ]
    return document_policies


def add_blueprint_permissions_for_zaaktypen_and_iots():
    zaaktypen = get_zaaktypen()
    roles = Role.objects.all()
    added = 0
    for zaaktype in zaaktypen:
        catalogus = fetch_catalogus(zaaktype.catalogus)

        for va in VertrouwelijkheidsAanduidingen.choices:
            zt_policy = {
                "catalogus": catalogus.domein,
                "zaaktype_omschrijving": zaaktype.omschrijving,
                "max_va": va[0],
            }
            document_policies = generate_document_policies(zt_policy, catalogus, va)
            for role in roles:
                obj, created = BlueprintPermission.objects.get_or_create(
                    role=role,
                    policy=zt_policy,
                    object_type=PermissionObjectTypeChoices.zaak,
                )
                if created:
                    added += 1

                for doc_policy in document_policies:
                    permission, created = BlueprintPermission.objects.get_or_create(
                        role=role,
                        object_type=PermissionObjectTypeChoices.document,
                        policy=doc_policy,
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
