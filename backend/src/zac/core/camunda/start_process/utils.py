from typing import List

from django.utils.translation import gettext_lazy as _

from zac.api.context import ZaakContext
from zac.core.services import (
    get_eigenschappen,
    get_rollen,
    get_roltypen,
    get_zaak_eigenschappen,
)

from .models import CamundaStartProcessForm, ProcessEigenschap
from .serializers import ProcessRolSerializer


def get_required_rollen(
    zaak_context: ZaakContext, camunda_start_process_form: CamundaStartProcessForm
) -> List[ProcessRolSerializer]:
    # Get all rollen that are already created and check if any of them
    # match the required rollen. Drop those that are already created.
    rollen = get_rollen(zaak_context.zaak)
    roltypen = {roltype.url: roltype for roltype in get_roltypen(zaak_context.zaaktype)}
    # resolve roltypen to rollen
    already_set_roltype = []
    for rol in rollen:
        rol.roltype = roltypen[rol.roltype]
        already_set_roltype.append(rol.roltype.omschrijving)

    # Get all required rollen from CamundaStartProcessForm
    process_rollen = camunda_start_process_form.processrol_set.all()
    required_process_rollen = []
    omschrijving_to_roltypen_map = {
        roltype.omschrijving: roltype for url, roltype in roltypen.items()
    }
    for process_rol in process_rollen:
        if process_rol.roltype_omschrijving in already_set_roltype:
            continue
        process_rol.roltype = omschrijving_to_roltypen_map[
            process_rol.roltype_omschrijving
        ]
        required_process_rollen.append(process_rol)
    return required_process_rollen


def get_required_zaakeigenschappen(
    zaak_context: ZaakContext, camunda_start_process_form: CamundaStartProcessForm
) -> List[ProcessEigenschap]:
    # Get all zaakeigenschappen and check if any of them match the
    # required zaakeigenschappen. Drop those that are already created.
    zaakeigenschappen = [
        zei.eigenschap.eigenschapnaam
        for zei in get_zaak_eigenschappen(zaak_context.zaak)
    ]
    eigenschappen = {
        ei.eigenschaapnaam: ei for ei in get_eigenschappen(zaak_context.zaaktype)
    }
    required_eigenschappen = camunda_start_process_form.processeigenschap_set.all()
    required_process_eigenschappen = []
    for ei in required_eigenschappen:
        if ei.eigenschapnaam in zaakeigenschappen.keys():
            continue

        ei.eigenschap = eigenschappen[ei.eigenschapnaam]
        required_process_eigenschappen.append(ei)

    return required_process_eigenschappen


def get_camunda_start_process_form_from_zaakcontext(
    zaak_context: ZaakContext,
) -> CamundaStartProcessForm:
    # Get related CamundaStartProcessForm
    camunda_start_process_form = CamundaStartProcessForm.objects.filter(
        zaaktype_catalogus=zaak_context.zaaktype.catalogus,
        zaaktype_identificatie=zaak_context.zaaktype.identificatie,
    )

    # Make sure it exists
    if not camunda_start_process_form.exists():
        raise RuntimeError(
            "Please create a camunda start process form for this zaaktype first."
        )
    else:
        camunda_start_process_form = camunda_start_process_form[0]
    return camunda_start_process_form
