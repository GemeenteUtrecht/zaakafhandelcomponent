from typing import List

from zgw_consumers.api_models.catalogi import InformatieObjectType

from ..services import fetch_zaaktype, get_informatieobjecttypen_for_zaaktype, get_zaak


def get_informatieobjecttypen_for_zaak(url: str) -> List[InformatieObjectType]:
    zaak = get_zaak(zaak_url=url)
    zaak.zaaktype = fetch_zaaktype(zaak.zaaktype)
    informatieobjecttypen = get_informatieobjecttypen_for_zaaktype(zaak.zaaktype)
    return informatieobjecttypen
