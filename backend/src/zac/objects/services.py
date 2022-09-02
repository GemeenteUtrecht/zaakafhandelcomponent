import logging
from typing import Dict, List, Optional

from django.utils.translation import ugettext_lazy as _

from djangorestframework_camel_case.settings import api_settings
from djangorestframework_camel_case.util import underscoreize
from furl import furl
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.zaken import ZaakObject

from zac.core.camunda.start_process.data import StartCamundaProcessForm
from zac.core.models import MetaObjectTypesConfig
from zac.core.services import fetch_catalogus, get_zaakobjecten, search_objects
from zac.objects.checklists.data import Checklist, ChecklistType
from zgw.models import Zaak

logger = logging.getLogger(__name__)
perf_logger = logging.getLogger("performance")


def _search_meta_objects(
    attribute_name: str,
    zaak: Optional[Zaak] = None,
    zaaktype: Optional[ZaakType] = None,
    unique: bool = False,
) -> List[dict]:
    config = MetaObjectTypesConfig.get_solo()
    ot_url = getattr(config, attribute_name)
    if not ot_url:
        logger.warning(
            "`{attr}` objecttype is not configured in core configuration or does not exist in the configured objecttype service.".format(
                attr=attribute_name
            )
        )
        return []

    object_filters = {"type": ot_url, "data_attrs": ["meta__icontains__true"]}
    if zaaktype:
        catalogus = fetch_catalogus(zaaktype.catalogus)
        object_filters["data_attrs"] += [
            f"zaaktypeIdentificaties__icontains__{zaaktype.identificatie}",
            f"zaaktypeCatalogus__exact__{catalogus.domein}",
        ]

    if zaak:
        object_filters["data_attrs"] += [f"zaak__icontains__{zaak.url}"]

    object_filters["data_attrs"] = ",".join(object_filters["data_attrs"])
    meta_objects = search_objects(object_filters)

    if not meta_objects:
        logger.warning("No `{url}` object is found.".format(url=ot_url))

    if unique and len(meta_objects) > 1:
        logger.warning("More than 1 `{url}` object is found.".format(url=ot_url))

    return meta_objects


###################################################
#               ZaaktypeAttributes                #
###################################################


def fetch_zaaktypeattributen_objects(zaaktype: Optional[ZaakType] = None) -> List[dict]:
    return _search_meta_objects("zaaktype_attribute_objecttype", zaaktype=zaaktype)


###################################################
#               StartCamundaProces                #
###################################################


def fetch_start_camunda_process_form(
    zaaktype: ZaakType,
) -> Optional[StartCamundaProcessForm]:
    start_camunda_process_form = _search_meta_objects(
        "start_camunda_process_form_objecttype", zaaktype=zaaktype, unique=True
    )
    if not start_camunda_process_form:
        return None

    return factory(
        StartCamundaProcessForm, start_camunda_process_form[0]["record"]["data"]
    )


###################################################
#                   Checklists                    #
###################################################


def fetch_checklisttype_object(
    zaaktype: ZaakType,
) -> Optional[Dict]:
    if obj := _search_meta_objects(
        "checklisttype_objecttype", zaaktype=zaaktype, unique=True
    ):
        return obj[0]
    return None


def fetch_checklisttype(
    zaaktype: ZaakType,
) -> Optional[ChecklistType]:
    checklisttype = fetch_checklisttype_object(zaaktype)
    if checklisttype:
        return factory(
            ChecklistType,
            underscoreize(
                checklisttype["record"]["data"],
                **api_settings.JSON_UNDERSCOREIZE,
            ),
        )
    return None


def fetch_checklist_object(
    zaak: Zaak,
) -> Optional[Dict]:
    if objs := _search_meta_objects("checklist_objecttype", zaak=zaak, unique=True):
        return objs[0]
    return None


def fetch_checklist(zaak: Zaak) -> Optional[Checklist]:
    checklist_object_data = fetch_checklist_object(zaak)

    if checklist_object_data:
        from zac.objects.checklists.api.serializers import ChecklistSerializer

        serializer = ChecklistSerializer(
            data=underscoreize(
                checklist_object_data["record"]["data"],
                **api_settings.JSON_UNDERSCOREIZE,
            ),
            context={"zaak": zaak},
        )
        serializer.is_valid(raise_exception=True)
        return factory(Checklist, serializer.validated_data)
    return None


def fetch_checklist_zaakobject(
    zaak: Zaak,
) -> Optional[ZaakObject]:
    checklist_object = fetch_checklist_object(zaak)
    if not checklist_object:
        return None

    zaakobjecten = get_zaakobjecten(zaak)
    for zo in zaakobjecten:
        if zo.object == checklist_object["url"]:
            return zo

    logger.warning("A checklist object was found but wasn't related to the ZAAK.")
    return None
