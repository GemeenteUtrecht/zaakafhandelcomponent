from typing import List

from django.db.models import Prefetch
from django.utils.translation import gettext_lazy as _

from zgw_consumers.api_models.catalogi import ZaakType

from zac.api.context import ZaakContext
from zac.core.services import (
    get_eigenschappen,
    get_informatieobjecttypen_for_zaaktype,
    get_rollen,
    get_roltypen,
    get_zaak_eigenschappen,
    resolve_documenten_informatieobjecttypen,
)

from .models import (
    CamundaStartProcess,
    ProcessEigenschap,
    ProcessEigenschapChoice,
    ProcessInformatieObject,
    ProcessRol,
)


def get_required_process_informatie_objecten(
    zaak_context: ZaakContext, camunda_start_process: CamundaStartProcess
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

    # Get all required process informatie objecten from CamundaStartProcess
    pi_objecten = camunda_start_process.processinformatieobject_set.all()
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
    zaak_context: ZaakContext, camunda_start_process: CamundaStartProcess
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

    # Get all required rollen from CamundaStartProcess
    process_rollen = camunda_start_process.processrol_set.all()
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
    zaak_context: ZaakContext, camunda_start_process: CamundaStartProcess
) -> List[ProcessEigenschap]:
    # Get all zaakeigenschappen and check if any of them match the
    # required zaakeigenschappen. Drop those that are already created.
    zaak_context.zaak.zaaktype = zaak_context.zaaktype
    zaakeigenschappen = [
        zei.eigenschap.naam for zei in get_zaak_eigenschappen(zaak_context.zaak)
    ]
    eigenschappen = {ei.naam: ei for ei in get_eigenschappen(zaak_context.zaaktype)}
    required_eigenschappen = camunda_start_process.processeigenschap_set.all()
    required_process_eigenschappen = []
    for ei in required_eigenschappen:
        if ei.eigenschapnaam not in zaakeigenschappen:
            ei.eigenschap = eigenschappen[ei.eigenschapnaam]
            required_process_eigenschappen.append(ei)

    return required_process_eigenschappen


def get_camunda_start_form_for_zaaktypen(zten: List[ZaakType]):
    process_forms = CamundaStartProcess.objects.prefetch_related(
        Prefetch(
            "processeigenschap_set",
            queryset=ProcessEigenschap.objects.prefetch_related(
                Prefetch(
                    "processeigenschapchoice_set",
                    queryset=ProcessEigenschapChoice.objects.all().order_by("label"),
                )
            ).all(),
        )
    ).filter(
        zaaktype_catalogus__in=[zt.catalogus for zt in zten],
        zaaktype_identificatie__in=[zt.identificatie for zt in zten],
    )
    return process_forms
