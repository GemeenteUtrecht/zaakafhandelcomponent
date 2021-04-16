from datetime import datetime

from django.db import migrations
from django.utils import timezone

from zac.core.services import get_zaaktypen
from zac.core.permissions import zaken_download_documents

from ..constants import AccessRequestResult, PermissionObjectType


def migrate_to_permission_definitions(apps, _):
    AccessRequest = apps.get_model("accounts", "AccessRequest")
    PermissionDefinition = apps.get_model("accounts", "PermissionDefinition")
    PermissionSet = apps.get_model("accounts", "PermissionSet")

    # migrate permission sets as blueprint permission definitions
    zaaktypen = get_zaaktypen()

    for permission_set in PermissionSet.objects.exclude(
        zaaktype_identificaties=[], authorizationprofile=None
    ):
        # transform zaaktype_identificaties to omschrijving
        zaaktype_omschrijvings = {
            zaaktype.omschrijving
            for zaaktype in zaaktypen
            if zaaktype.catalogus == permission_set.catalogus
            and zaaktype.identificatie in permission_set.zaaktype_identificaties
        }
        for zaaktype_omschrijving in zaaktype_omschrijvings:
            for permission_name in permission_set.permissions:
                # exclude permissions with different shape
                if permission_name != zaken_download_documents.name:
                    zaak_permission_definition = PermissionDefinition.objects.create(
                        object_type=PermissionObjectType.zaak,
                        permission=permission_name,
                        policy={
                            "catalogus": permission_set.catalogus,
                            "zaaktype_omschrijving": zaaktype_omschrijving,
                            "max_va": permission_set.max_va,
                        },
                    )

                for auth_profile in permission_set.authorizationprofile_set.all():
                    auth_profile.permission_definitions.add(zaak_permission_definition)

        for doc_permission in permission_set.informatieobjecttypepermission_set.all():
            # exclude permissions with different shape
            if zaken_download_documents.name in permission_set.permissions:
                doc_permission_definition = PermissionDefinition.objects.create(
                    object_type=PermissionObjectType.document,
                    permission=zaken_download_documents.name,
                    policy={
                        "catalogus": doc_permission.catalogus,
                        "iotype_omschrijving": doc_permission.omschrijving,
                        "max_va": doc_permission.max_va,
                    },
                )

                for auth_profile in permission_set.authorizationprofile_set.all():
                    auth_profile.permission_definitions.add(doc_permission_definition)

    # migrate approved access requests as atomic permission definitions
    for access_request in AccessRequest.objects.filter(
        result=AccessRequestResult.approve
    ):
        start_date = (
            timezone.make_aware(
                datetime.combine(access_request.start_date, datetime.min.time())
            )
            if access_request.start_date
            else None
        )
        end_date = (
            timezone.make_aware(
                datetime.combine(access_request.end_date, datetime.min.time())
            )
            if access_request.end_date
            else None
        )
        atomic_permission = PermissionDefinition.objects.create(
            object_type=PermissionObjectType.zaak,
            object_url=AccessRequest.zaak,
            permission="zaken:inzien",
            start_date=start_date,
            end_date=end_date,
        )
        access_request.requester.permission_definitions.add(atomic_permission)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0024_auto_20210317_1100"),
        ("zgw_consumers", "0012_auto_20210104_1039"),
    ]

    operations = [
        migrations.RunPython(
            migrate_to_permission_definitions, migrations.RunPython.noop
        ),
    ]
