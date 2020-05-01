import rules
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from zac.accounts.permissions import VA_ORDER, PermissionSet

from .permissions import zaken_inzien


@rules.predicate
def can_read_zaak(user, zaak):
    # check permission sets
    zt_identificatie = zaak.zaaktype.identificatie

    zaak_va = VA_ORDER[zaak.vertrouwelijkheidaanduiding]

    perm_sets = (
        PermissionSet.objects.filter(
            authorizationprofile__user=user,
            catalogus=zaak.zaaktype.catalogus,
            permissions__contains=[zaken_inzien.name],
            zaaktype_identificaties__contains=[zt_identificatie],
        )
        .annotate(
            _max_va_order=VertrouwelijkheidsAanduidingen.get_order_expression("max_va")
        )
        .filter(_max_va_order__gte=zaak_va)
    )

    return perm_sets.exists()


rules.add_rule(zaken_inzien.name, can_read_zaak)
