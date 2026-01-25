from datetime import date

from django_camunda.api import get_task_variables
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType

from zac.camunda.data import Task
from zac.core.services import _get_from_catalogus, fetch_zaaktype


class MissingVariable(Exception):
    """
    Taken from BPTL.tasks.base.py
    """


def check_variable(variables: dict, name: str, empty_allowed=False):
    """
    Taken from BPTL.tasks.base.py
    """
    error = MissingVariable(f"The variable {name} is missing or empty.")
    if name not in variables:
        raise error

    elif (
        not empty_allowed
        and not variables[name]
        and not isinstance(variables[name], bool)
    ):
        raise error

    return variables[name]


def get_zaaktype_from_identificatie(task: Task) -> ZaakType:
    """
    Taken from BPTL.work_units_zgw_tasks.zaak.py and altered slightly for purposes in zac.
    """
    variables = get_task_variables(task.id)
    if not (zaaktype_url := variables.get("zaaktype", "")):
        catalogus_domein = check_variable(variables, "catalogusDomein")
        catalogus_rsin = variables.get("catalogusRSIN") or check_variable(
            variables, "organisatieRSIN"
        )
        zaaktype_identificatie = check_variable(variables, "zaaktypeIdentificatie")

        request_kwargs = {"domein": catalogus_domein, "rsin": catalogus_rsin}
        catalogus = _get_from_catalogus("catalogus", **request_kwargs)
        try:
            catalogus_url = catalogus[0]["url"]
        except (KeyError, IndexError):
            raise ValueError(
                "No catalogus found with domein %s and RSIN %s."
                % (catalogus_domein, catalogus_rsin)
            )

        request_kwargs = {
            "catalogus": catalogus_url,
            "identificatie": zaaktype_identificatie,
        }
        zaaktypen = _get_from_catalogus("zaaktype", **request_kwargs)
        if len(zaaktypen) == 0:
            raise ValueError(
                "No zaaktype was found with catalogus %s and identificatie %s."
                % (
                    catalogus_url,
                    zaaktype_identificatie,
                )
            )

        zaaktypen = [factory(ZaakType, zaaktype) for zaaktype in zaaktypen]

        def _filter_on_geldigheid(zaaktype: ZaakType) -> bool:
            if zaaktype.einde_geldigheid:
                return (
                    zaaktype.begin_geldigheid
                    <= date.today()
                    <= zaaktype.einde_geldigheid
                )
            else:
                return zaaktype.begin_geldigheid <= date.today()

        zaaktypen = [zt for zt in zaaktypen if _filter_on_geldigheid(zt)]
        # Sketchy logic for edge cases:
        # Use the ZT with none as einde geldigheid or einde geldigheid that's further into the future
        # in the edge case that einde geldigheid old zaaktype is today and a new zaaktype is geldig from today.
        if len(zaaktypen) > 1:
            zaaktypen_without_einde_geldigheid = [
                zt for zt in zaaktypen if not zt.einde_geldigheid
            ]

            # If this does not exist -> get one with einde_geldigheid most distant into the future
            if len(zaaktypen_without_einde_geldigheid) == 0:
                max_einde_geldigheid = max([zt.einde_geldigheid for zt in zaaktypen])
                zaaktypen = [
                    zt
                    for zt in zaaktypen
                    if zt.einde_geldigheid == max_einde_geldigheid
                ]
            else:
                zaaktypen = zaaktypen_without_einde_geldigheid

        if len(zaaktypen) != 1:
            raise ValueError(
                "No%s zaaktype was found with catalogus %s, identificatie %s with begin_geldigheid <= %s <= einde_geldigheid."
                % (
                    "" if len(zaaktypen) == 0 else " unique",
                    catalogus_url,
                    zaaktype_identificatie,
                    date.today(),
                )
            )

        zaaktype = zaaktypen[0]
    else:
        zaaktype = fetch_zaaktype(zaaktype_url)
    return zaaktype
