from django.db import migrations
from zac.accounts.constants import (
    PermissionReason,
    AccessRequestResult,
    PermissionObjectType,
)
from zac.core.services import get_zaak, get_rollen
from zac.contrib.kownsl.api import get_review_requests
from zac.contrib.kownsl.data import KownslTypes


def get_reason(user_atomic_permission) -> str:
    user = user_atomic_permission.user
    object_url = user_atomic_permission.atomic_permission.object_url

    if getattr(user_atomic_permission, "accessrequest", None):
        return PermissionReason.toegang_verlenen

    if user.initiated_requests.filter(
        zaak=object_url, result=AccessRequestResult.approve
    ):
        return PermissionReason.toegang_verlenen

    if user.activity_set.filter(zaak=object_url).exists():
        return PermissionReason.activiteit

    zaak = get_zaak(zaak_url=object_url)
    rollen = get_rollen(zaak=zaak)

    for rol in rollen:
        if (
            rol.betrokkene_type == "medewerker"
            and rol.omschrijving_generiek == "behandelaar"
            and rol.betrokkene_identificatie.get("identificatie") == user.username
        ):
            return PermissionReason.betrokkene

    review_requests = get_review_requests(zaak)
    for review_request in review_requests:
        if user.username in list(review_request.user_deadlines.keys()):
            return (
                PermissionReason.accordeur
                if review_request.review_type == KownslTypes.approval
                else PermissionReason.adviseur
            )

    return ""


def load_permission_reason(apps, _):
    UserAtomicPermission = apps.get_model("accounts", "UserAtomicPermission")

    for user_atomic_permission in UserAtomicPermission.objects.select_related(
        "user", "atomic_permission"
    ).filter(reason="", atomic_permission__object_type=PermissionObjectType.zaak):
        reason = get_reason(user_atomic_permission)
        if reason:
            user_atomic_permission.reason = reason
            user_atomic_permission.save()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0035_useratomicpermission_reason"),
        ("activities", "0002_auto_20200805_1413"),
    ]

    operations = [
        migrations.RunPython(load_permission_reason, migrations.RunPython.noop)
    ]
