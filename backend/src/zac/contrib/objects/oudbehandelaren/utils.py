import datetime
from typing import Dict, Optional

from zgw_consumers.api_models.constants import RolOmschrijving

from zac.accounts.models import User
from zac.camunda.constants import AssigneeTypeChoices
from zac.core.camunda.utils import resolve_assignee
from zac.core.services import fetch_rol, update_object_record_data
from zgw.models import Zaak

from ..services import (
    create_meta_object_and_relate_to_zaak,
    fetch_oudbehandelaren_object,
)


def register_old_behandelaar(
    zaak: Zaak, rol_url: str, user: Optional[User] = None
) -> Optional[Dict]:
    rol = fetch_rol(rol_url)
    if rol.omschrijving_generiek not in [
        RolOmschrijving.behandelaar,
        RolOmschrijving.initiator,
    ]:
        return None

    object = fetch_oudbehandelaren_object(zaak)
    create = False
    if not object:
        create = True
        data = {"zaak": zaak.url, "oudbehandelaren": []}
    else:
        data = object["record"]["data"]

    identificatie = rol.get_identificatie()
    try:
        rol_user = resolve_assignee(identificatie)
    except RuntimeError:
        rol_user = None

    data["oudbehandelaren"].append(
        {
            "email": rol_user.email if rol_user else "",
            "ended": datetime.datetime.now().isoformat(),
            "started": rol.registratiedatum.isoformat(),
            "identificatie": identificatie,
            "changed_by": (
                f"{AssigneeTypeChoices.user}:{user}" if user else "service-account"
            ),
        }
    )

    if create:
        object = create_meta_object_and_relate_to_zaak(
            "oudbehandelaren", data, zaak.url
        )
    else:
        object = update_object_record_data(object, data, user=user)

    return object
