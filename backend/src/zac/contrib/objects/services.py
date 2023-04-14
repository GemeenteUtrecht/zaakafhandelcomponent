import logging
from typing import Dict, List, Optional

from django.utils.translation import ugettext_lazy as _

from djangorestframework_camel_case.settings import api_settings
from djangorestframework_camel_case.util import underscoreize
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.zaken import ZaakObject
from zgw_consumers.concurrent import parallel

from zac.accounts.models import User
from zac.contrib.objects.checklists.data import Checklist, ChecklistType
from zac.core.camunda.start_process.data import StartCamundaProcessForm
from zac.core.models import MetaObjectTypesConfig
from zac.core.services import fetch_catalogus, get_zaakobjecten, search_objects
from zac.utils.decorators import cache
from zgw.models import Zaak

logger = logging.getLogger(__name__)
perf_logger = logging.getLogger("performance")
A_DAY = 60 * 60 * 24


def _search_meta_objects(
    attribute_name: str,
    zaak: Optional[Zaak] = None,
    zaaktype: Optional[ZaakType] = None,
    unique: bool = False,
    data_attrs: List = [],
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

    if data_attrs:
        object_filters["data_attrs"] += data_attrs

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


@cache("zaaktype_attribute_objecttype", timeout=A_DAY)
def fetch_zaaktypeattributen_objects() -> List[dict]:
    """
    Cache the broader group of zaaktype attributes to increase performance
    related to fetching meta objects.

    The key relates to the field name on MetaObjectsConfig singletonmodel
    found in zac.core.models.

    """
    if objs := _search_meta_objects("zaaktype_attribute_objecttype"):
        return [obj["record"]["data"] for obj in objs]
    return []


def fetch_zaaktypeattributen_objects_for_zaaktype(zaaktype: ZaakType):
    objs = fetch_zaaktypeattributen_objects()
    catalogus = fetch_catalogus(zaaktype.catalogus)
    return [
        obj["record"]["data"]
        for obj in objs
        if zaaktype.identificatie in obj["record"]["data"]["zaaktypeIdentificaties"]
        and catalogus.domein in obj["record"]["data"]["zaaktypeCatalogus"]
    ]


###################################################
#               StartCamundaProces                #
###################################################


@cache("start_camunda_process_form_objecttype", timeout=A_DAY)
def fetch_start_camunda_process_form() -> Optional[StartCamundaProcessForm]:
    """
    Cache the broader group of start camunda process forms to increase performance
    related to fetching meta objects.

    The key relates to the field name on MetaObjectsConfig singletonmodel
    found in zac.core.models.

    """
    start_camunda_process_form = _search_meta_objects(
        "start_camunda_process_form_objecttype",
    )
    if not start_camunda_process_form:
        return None

    return factory(
        StartCamundaProcessForm, start_camunda_process_form[0]["record"]["data"]
    )


def fetch_start_camunda_process_form_for_zaaktype(
    zaaktype: ZaakType,
) -> Optional[StartCamundaProcessForm]:
    forms = fetch_start_camunda_process_form()

    if not forms:
        return None

    catalogus = fetch_catalogus(zaaktype.catalogus)
    forms = [
        form
        for form in forms
        if zaaktype.identificatie in form.zaaktype_identificaties
        and catalogus.domein in form.zaaktype_catalogus
    ]
    if len(forms) > 1:
        logger.warning(
            "More than 1 start_camunda_process_form_objecttype object is found."
        )
    return forms[0]


###################################################
#                   Checklists                    #
###################################################


@cache("checklisttype_objecttype", timeout=A_DAY)
def fetch_checklisttype_object(
    zaaktype: ZaakType,
) -> Optional[Dict]:
    """
    Cache the broader group of checklisttypes to increase performance
    related to fetching meta objects.

    The key relates to the field name on MetaObjectsConfig singletonmodel
    found in zac.core.models.

    """
    if objs := _search_meta_objects("checklisttype_objecttype"):
        return objs
    return None


def fetch_checklisttype(
    zaaktype: ZaakType,
) -> Optional[ChecklistType]:
    checklisttypes = fetch_checklisttype_object(zaaktype)
    if checklisttypes:
        catalogus = fetch_catalogus(zaaktype.catalogus)
        checklisttypes = [
            clt
            for clt in checklisttypes
            if zaaktype.identificaties
            in clt["record"]["data"]["zaaktypeIdentificaties"]
            and catalogus.domein in clt["record"]["data"]["zaaktypeCatalogus"]
        ]
        if len(checklisttypes) > 1:
            logger.warning("More than 1 checklisttype_objecttype object is found.")

        return factory(
            ChecklistType,
            underscoreize(
                checklisttypes[0]["record"]["data"],
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
        from zac.contrib.objects.checklists.api.serializers import ChecklistSerializer

        serializer = ChecklistSerializer(
            data=underscoreize(
                checklist_object_data["record"]["data"],
                **api_settings.JSON_UNDERSCOREIZE,
            ),
        )
        serializer.is_valid(raise_exception=True)
        return factory(Checklist, serializer.validated_data)
    return None


def fetch_all_checklists_for_user(user: User) -> List[dict]:
    data_attrs = [f"answers__answer__userAssignee__exact__{user.username}"]
    if objs := _search_meta_objects("checklist_objecttype", data_attrs=data_attrs):
        return [
            underscoreize(
                obj["record"]["data"],
                **api_settings.JSON_UNDERSCOREIZE,
            )
            for obj in objs
        ]
    return []


def fetch_all_checklists_for_user_groups(user: User) -> List[dict]:
    data_attrs_list = [
        [f"answers__answer__groupAssignee__exact__{group.name}"]
        for group in user.groups.all()
    ]

    def _search_checklists_objects(data_attrs: List[str]) -> List[dict]:
        if objs := _search_meta_objects("checklist_objecttype", data_attrs=data_attrs):
            return [
                underscoreize(
                    obj["record"]["data"],
                    **api_settings.JSON_UNDERSCOREIZE,
                )
                for obj in objs
            ]
        return []

    with parallel() as executor:
        results = executor.map(_search_checklists_objects, data_attrs_list)

    final_results = []
    for result in results:
        if result:
            final_results += result
    return final_results


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
