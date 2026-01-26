from typing import List

from zgw_consumers.api_models.base import factory

from zac.api.context import ZaakContext
from zac.contrib.objects.services import fetch_zaaktypeattributen_objects_for_zaaktype
from zac.core.camunda.start_process.data import ProcessEigenschapChoice
from zac.core.services import (
    get_eigenschappen,
    get_informatieobjecttypen_for_zaaktype,
    get_rollen,
    get_roltypen,
    get_zaakeigenschappen,
)
from zac.elasticsearch.searches import count_by_iot_in_zaak

from .data import (
    ProcessEigenschap,
    ProcessInformatieObject,
    ProcessRol,
    StartCamundaProcessForm,
)


def get_required_process_informatie_objecten(
    zaak_context: ZaakContext, camunda_start_process: StartCamundaProcessForm
) -> List[ProcessInformatieObject]:
    iots = {
        iot.omschrijving: iot
        for iot in get_informatieobjecttypen_for_zaaktype(zaak_context.zaaktype)
    }
    # Get the counts of all the documents that are already uploaded and add them to
    # already_uploaded_informatieobjecten if their
    # informatieobjecttype.omschrijving matches.

    iots_found_for_zaak = count_by_iot_in_zaak(zaak_context.zaak.url)

    # Get all required process informatie objecten from StartCamundaProcessForm
    pi_objecten = camunda_start_process.process_informatie_objecten
    required_process_informatie_objecten = []
    for piobject in pi_objecten:
        piobject.informatieobjecttype = None
        piobject.informatieobjecttype = iots.get(
            piobject.informatieobjecttype_omschrijving, None
        )

        if not piobject.informatieobjecttype:
            raise RuntimeError(
                "Could not find an INFORMATIEOBJECTTYPE with omschrijving {omschrijving} for ZAAKTYPE {zaaktype}.".format(
                    omschrijving=piobject.informatieobjecttype_omschrijving,
                    zaaktype=zaak_context.zaaktype.omschrijving,
                )
            )

        docs = iots_found_for_zaak.get(piobject.informatieobjecttype.omschrijving, 0)

        if docs:
            piobject.already_uploaded_informatieobjecten = docs

        if docs and not piobject.allow_multiple:
            continue

        required_process_informatie_objecten.append(piobject)

    return required_process_informatie_objecten


def get_required_rollen(
    zaak_context: ZaakContext, camunda_start_process: StartCamundaProcessForm
) -> List[ProcessRol]:
    # Get all rollen that are already created and check if any of them
    # match the required rollen. Drop those that are already created.
    rollen = get_rollen(zaak_context.zaak)
    roltypen = {roltype.url: roltype for roltype in get_roltypen(zaak_context.zaaktype)}

    # resolve roltypen to rollen
    already_set_roltype = []
    for rol in rollen:
        rol.roltype = roltypen[rol.roltype]
        already_set_roltype.append(rol.roltype.omschrijving)

    # Get all required rollen from StartCamundaProcessForm
    process_rollen = camunda_start_process.process_rollen
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
    zaak_context: ZaakContext, camunda_start_process: StartCamundaProcessForm
) -> List[ProcessEigenschap]:
    # Get all zaakeigenschappen and check if any of them match the
    # required zaakeigenschappen. Drop those that are already created.
    zaak_context.zaak.zaaktype = zaak_context.zaaktype
    zaakeigenschappen = [
        zei.eigenschap.naam for zei in get_zaakeigenschappen(zaak_context.zaak)
    ]
    eigenschappen = {ei.naam: ei for ei in get_eigenschappen(zaak_context.zaaktype)}
    required_eigenschappen = camunda_start_process.process_eigenschappen
    zaakattributes = {
        data["naam"]: data
        for data in fetch_zaaktypeattributen_objects_for_zaaktype(
            zaaktype=zaak_context.zaaktype
        )
    }
    required_process_eigenschappen = []
    for ei in required_eigenschappen:
        if ei.eigenschapnaam not in zaakeigenschappen:
            ei.eigenschap = eigenschappen[ei.eigenschapnaam]
            if ei.eigenschapnaam in zaakattributes and (
                enum := zaakattributes[ei.eigenschapnaam].get("enum")
            ):
                ei.choices = factory(
                    ProcessEigenschapChoice,
                    [{"value": choice, "label": choice} for choice in enum],
                )
            elif enum := ei.eigenschap.specificatie.waardenverzameling:
                ei.choices = factory(
                    ProcessEigenschapChoice,
                    [{"value": choice, "label": choice} for choice in enum],
                )
            else:
                ei.choices = []
            required_process_eigenschappen.append(ei)

    return required_process_eigenschappen
