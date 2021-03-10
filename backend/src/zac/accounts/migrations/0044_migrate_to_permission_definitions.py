from django.db import migrations
from ..constants import AccessRequestResult, PermissionObjectType
from zac.core.services import get_zaaktypen


def migrate_to_permission_definitions(apps, _):
    AccessRequest = apps.get_model("accounts", "AccessRequest")
    PermissionDefinition = apps.get_model("accounts", "PermissionDefinition")
    PermissionSet = apps.get_model("accounts", "PermissionSet")

    # migrate permission sets as blueprint permission definitions
    zaaktypen = get_zaaktypen()

    for permission_set in PermissionSet.objects.exclude(
        zaaktype_identificaties=[], informatieobjecttypepermission=None
    ).exclude(authorizationprofile=None):
        # transform zaaktype_identificaties to omschriving
        zaaktype_omschrijvings = {
            zaaktype.omschrijving
            for zaaktype in zaaktypen
            if zaaktype.catalogus == permission_set.catalogus
            and zaaktype.identificatie in permission_set.zaaktype_identificaties
        }
        for zaaktype_omschrijving in zaaktype_omschrijvings:
            for permission_name in permission_set.permissions:
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
            for permission_name in permission_set.permissions:
                doc_permission_definition = PermissionDefinition.objects.create(
                    object_type=PermissionObjectType.document,
                    permission=permission_name,
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
        atomic_permission = PermissionDefinition.objects.create(
            object_type=PermissionObjectType.zaak,
            object_url=AccessRequest.zaak,
            permission="zaken:inzien",
            start_date=AccessRequest.start_date,
            end_date=AccessRequest.end_date,
        )
        access_request.requester.permission_definitions.add(atomic_permission)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0023_auto_20210309_1810"),
    ]

    operations = [
        migrations.RunPython(
            migrate_to_permission_definitions, migrations.RunPython.noop
        ),
    ]
