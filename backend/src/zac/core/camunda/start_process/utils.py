from typing import List

from django.utils.translation import gettext_lazy as _

from zgw_consumers.api_models.base import factory

from zac.api.context import ZaakContext
from zac.core.camunda.start_process.data import ProcessEigenschapChoice
from zac.core.services import (
    get_eigenschappen,
    get_informatieobjecttypen_for_zaaktype,
    get_rollen,
    get_roltypen,
    get_zaak_eigenschappen,
    resolve_documenten_informatieobjecttypen,
)
from zac.objects.services import fetch_zaaktypeattributen_objects

from .data import (
    ProcessEigenschap,
    ProcessInformatieObject,
    ProcessRol,
    StartCamundaProcessForm,
)


def get_required_process_informatie_objecten(
    zaak_context: ZaakContext, camunda_start_process: StartCamundaProcessForm
) -> List[ProcessInformatieObject]:
    iots = get_informatieobjecttypen_for_zaaktype(zaak_context.zaaktype)
    # Get all documents that are already uploaded and add them to
    # already_uploaded_informatieobjecten if their
    # informatieobjecttype.omschrijving matches.
    zaak_context.documents = resolve_documenten_informatieobjecttypen(
        zaak_context.documents
    )
    ziot_omschrijvingen_to_doc_map = {}
    for doc in zaak_context.documents:
        if (
            omschrijving := doc.informatieobjecttype.omschrijving
        ) not in ziot_omschrijvingen_to_doc_map:
            ziot_omschrijvingen_to_doc_map[omschrijving] = [doc]
        else:
            ziot_omschrijvingen_to_doc_map[omschrijving].append(doc)

    # Get all required process informatie objecten from StartCamundaProcessForm
    pi_objecten = camunda_start_process.process_informatie_objecten
    required_process_informatie_objecten = []
    for piobject in pi_objecten:
        piobject.informatieobjecttype = None
        for iot in iots:
            if iot.omschrijving == piobject.informatieobjecttype_omschrijving:
                piobject.informatieobjecttype = iot
        if not piobject.informatieobjecttype:
            raise RuntimeError(
                "Could not find an INFORMATIEOBJECTTYPE with omschrijving {omschrijving} for ZAAKTYPE {zaaktype}.".format(
                    omschrijving=piobject.informatieobjecttype_omschrijving,
                    zaaktype=zaak_context.zaaktype.omschrijving,
                )
            )

        docs = ziot_omschrijvingen_to_doc_map.get(
            piobject.informatieobjecttype_omschrijving
        )
        if docs:
            piobject.already_uploaded_informatieobjecten = [doc.url for doc in docs]
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
        zei.eigenschap.naam for zei in get_zaak_eigenschappen(zaak_context.zaak)
    ]
    eigenschappen = {ei.naam: ei for ei in get_eigenschappen(zaak_context.zaaktype)}
    required_eigenschappen = camunda_start_process.process_eigenschappen
    zaakattributes = {
        data["naam"]: data
        for data in fetch_zaaktypeattributen_objects(zaaktype=zaak_context.zaaktype)
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
