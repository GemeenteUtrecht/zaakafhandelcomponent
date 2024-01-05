import datetime
from typing import Dict, Optional

from djangorestframework_camel_case.settings import api_settings
from djangorestframework_camel_case.util import camelize
from zgw_consumers.api_models.constants import RolOmschrijving

from zac.accounts.models import User
from zac.core.models import MetaObjectTypesConfig
from zac.core.services import (
    create_object,
    fetch_objecttype,
    fetch_rol,
    relate_object_to_zaak,
    update_object_record_data,
)
from zgw.models import Zaak

from ..services import fetch_oudbehandelaren_object


def register_old_behandelaar(zaak: Zaak, rol_url: str, user: User) -> Optional[Dict]:
    rol = fetch_rol(rol_url)
    if rol.omschrijving_generiek not in [
        RolOmschrijving.behandelaar,
        RolOmschrijving.initiator,
    ]:
        return None

    oudbehandelaren_obj_type_url = (
        MetaObjectTypesConfig.get_solo().oudbehandelaren_objecttype
    )
    oudbehandelaren_obj_type = fetch_objecttype(oudbehandelaren_obj_type_url)

    # Get latest version of objecttype
    latest_version = fetch_objecttype(max(oudbehandelaren_obj_type["versions"]))

    object = fetch_oudbehandelaren_object(zaak)
    create = False
    if not object:
        create = True
        data = {"zaak": zaak.url, "oudbehandelaren": []}
    else:
        data = object["record"]["data"]

    data["oudbehandelaren"].append(
        {
            "email": user.email,
            "ended": datetime.datetime.now().isoformat(),
            "started": rol.registratiedatum.isoformat(),
            "identificatie": rol.get_identificatie(),
        }
    )

    if create:
        object = create_object(
            {
                "type": oudbehandelaren_obj_type["url"],
                "record": {
                    "typeVersion": latest_version["version"],
                    "data": camelize(data, **api_settings.JSON_UNDERSCOREIZE),
                    "startAt": datetime.date.today().isoformat(),
                },
            }
        )
        relate_object_to_zaak(
            {
                "zaak": zaak.url,
                "object": object["url"],
                "object_type": "overige",
                "object_type_overige": oudbehandelaren_obj_type["name"],
                "object_type_overige_definitie": {
                    "url": latest_version["url"],
                    "schema": ".jsonSchema",
                    "objectData": ".record.data",
                },
                "relatieomschrijving": "Oudbehandelaren van de ZAAK.",
            }
        )
    else:
        object = update_object_record_data(object, data, user=user)

    return object
