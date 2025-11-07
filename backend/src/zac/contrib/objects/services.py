import datetime
import logging
from typing import Callable, Dict, List, Optional, Tuple, Union
from uuid import uuid4

from django.conf import settings
from django.http import Http404
from django.utils.translation import gettext_lazy as _

from djangorestframework_camel_case.settings import api_settings
from djangorestframework_camel_case.util import camelize, underscoreize
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.zaken import ZaakObject
from zgw_consumers.concurrent import parallel

from zac.accounts.models import User
from zac.contrib.objects.checklists.data import Checklist, ChecklistType
from zac.core.camunda.start_process.data import StartCamundaProcessForm
from zac.core.models import MetaObjectTypesConfig
from zac.core.services import (
    create_object,
    fetch_catalogus,
    fetch_objecttype,
    get_zaakobjecten,
    relate_object_to_zaak,
    search_objects,
    update_object_record_data,
)
from zac.core.utils import A_DAY
from zac.utils.decorators import cache
from zgw.models import Zaak

from .kownsl.data import ReviewRequest, Reviews
from .oudbehandelaren.data import Oudbehandelaren

logger = logging.getLogger(__name__)


def _search_meta_objects(
    objecttype_name: str,
    zaak: Optional[Zaak] = None,
    zaaktype: Optional[ZaakType] = None,
    unique: bool = False,
    data_attrs: List = [],
    paginated: bool = False,
    query_params: Optional[Dict] = None,
    extra_kwargs: Optional[Dict] = None,
    page_size: int = 100,
) -> Union[List[dict], Tuple[Dict, Dict]]:

    config = MetaObjectTypesConfig.get_solo()
    ot_url = getattr(config, objecttype_name, None)
    if not ot_url:
        logger.warning(
            "`{objecttype_name}` objecttype is not configured in core configuration or does not exist in the configured objecttype service.".format(
                objecttype_name=objecttype_name
            )
        )
        return []

    object_filters = {"type": ot_url, "data_attrs": []}
    if extra_kwargs:
        object_filters.update(extra_kwargs)

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

    if (not query_params) or ("pageSize" not in query_params):
        query_params = {"pageSize": page_size}

    if paginated:
        response, query_params = search_objects(
            object_filters, query_params=query_params
        )
        return response, query_params

    else:
        get_more = True
        meta_objects = []
        while get_more:
            response, query_params = search_objects(
                object_filters, query_params=query_params
            )
            meta_objects += response["results"]
            get_more = query_params.get("page", None)

    if not meta_objects:
        logger.warning("No `{url}` object is found.".format(url=ot_url))

    if unique and len(meta_objects) > 1:
        logger.warning("More than 1 `{url}` object is found.".format(url=ot_url))

    return meta_objects


def create_meta_object_and_relate_to_zaak(
    objecttype_str: str,
    data: Union[List, Dict],
    zaak: str,
    camelize_settings: Dict = api_settings.JSON_UNDERSCOREIZE,
) -> Dict:
    # Get URL-reference to objecttype
    objecttype_url = getattr(
        MetaObjectTypesConfig.get_solo(), f"{objecttype_str}_objecttype"
    )
    objecttype = fetch_objecttype(objecttype_url)

    # Get latest version of objecttype
    latest_version = fetch_objecttype(max(objecttype["versions"]))
    data = camelize(data, **camelize_settings)

    result = create_object(
        {
            "type": objecttype["url"],
            "record": {
                "typeVersion": latest_version["version"],
                "data": data,
                "startAt": datetime.date.today().isoformat(),
            },
        }
    )
    relate_object_to_zaak(
        {
            "zaak": zaak,
            "object": result["url"],
            "object_type": "overige",
            "object_type_overige": objecttype["name"],
            "object_type_overige_definitie": {
                "url": latest_version["url"],
                "schema": ".jsonSchema",
                "objectData": ".record.data",
            },
            "relatieomschrijving": f"{objecttype['name']} van de ZAAK.",
        }
    )
    return result


def _create_unique_uuid_for_object(func: Callable, counter=0) -> str:
    id = str(uuid4())
    # check if id exists:
    if func(id=id):
        if counter < 3:  # prevent infinite recursion
            return _create_unique_uuid_for_object(func, counter=counter + 1)
        else:
            raise RuntimeError(
                "Something went wrong - review requests with {id} already exists or?"
            )
    return id


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
        obj
        for obj in objs
        if zaaktype.identificatie in obj["zaaktypeIdentificaties"]
        and catalogus.domein in obj["zaaktypeCatalogus"]
    ]


###################################################
#               StartCamundaProces                #
###################################################


@cache("start_camunda_process_form_objecttype", timeout=A_DAY)
def fetch_start_camunda_process_form() -> Optional[List[StartCamundaProcessForm]]:
    """
    Cache the broader group of start camunda process forms to increase performance
    related to fetching meta objects.

    The key relates to the field name on MetaObjectsConfig singletonmodel
    found in zac.core.models.

    """
    start_camunda_process_forms = _search_meta_objects(
        "start_camunda_process_form_objecttype",
    )
    if not start_camunda_process_forms:
        return None

    return factory(
        StartCamundaProcessForm,
        [form["record"]["data"] for form in start_camunda_process_forms],
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

    if not forms:
        return None

    if len(forms) > 1:
        logger.warning(
            "More than 1 start_camunda_process_form_objecttype object is found."
        )

    return forms[0]


###################################################
#                   Checklists                    #
###################################################


@cache("checklisttype_objecttype", timeout=A_DAY)
def fetch_checklisttype_object() -> Optional[Dict]:
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
    checklisttypes = fetch_checklisttype_object()
    if not checklisttypes:
        return None

    catalogus = fetch_catalogus(zaaktype.catalogus)
    checklisttypes = [
        clt
        for clt in checklisttypes
        if zaaktype.identificatie in clt["record"]["data"]["zaaktypeIdentificaties"]
        and catalogus.domein in clt["record"]["data"]["zaaktypeCatalogus"]
    ]
    if not checklisttypes:
        return None

    if len(checklisttypes) > 1:
        logger.warning("More than 1 checklisttype_objecttype object is found.")

    return factory(ChecklistType, checklisttypes[0]["record"]["data"])


@cache("fetch_checklist_object:{zaak.url}", timeout=A_DAY)
def fetch_checklist_object(
    zaak: Zaak,
) -> Optional[Dict]:
    if objs := _search_meta_objects("checklist_objecttype", zaak=zaak, unique=True):
        return objs[0]
    return None


def fetch_checklist(
    zaak: Zaak, checklist_object_data: Optional[Dict] = None
) -> Optional[Checklist]:
    if not checklist_object_data:
        checklist_object_data = fetch_checklist_object(zaak)

    if checklist_object_data:
        return factory(Checklist, checklist_object_data["record"]["data"])
    return None


def fetch_all_unanswered_checklists_for_user(user: User) -> List[dict]:
    data_attrs = [f"answers__icontains__{user.username}", "locked__icontains__false"]
    if objs := _search_meta_objects("checklist_objecttype", data_attrs=data_attrs):
        checklists = [
            underscoreize(
                obj["record"]["data"],
                **api_settings.JSON_UNDERSCOREIZE,
            )
            for obj in objs
        ]
        filtered = []
        for checklist in checklists:
            if any(
                [
                    answer
                    for answer in checklist["answers"]
                    if user.username == answer.get("user_assignee")
                    and not answer["answer"]
                ]
            ):
                filtered.append(checklist)
        return filtered
    return []


def fetch_all_checklists_for_user_groups(user: User) -> List[dict]:
    groupnames = user.groups.all().values_list("name", flat=True)
    data_attrs_list = [[f"answers__icontains__{group}"] for group in groupnames]

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

    with parallel(max_workers=settings.MAX_WORKERS) as executor:
        results = executor.map(_search_checklists_objects, data_attrs_list)
    final_results = []
    for result in results:
        if result:
            filtered = []
            for checklist in result:
                if any(
                    [
                        answer
                        for answer in checklist["answers"]
                        if answer.get("group_assignee") in groupnames
                        and not answer["answer"]
                    ]
                ):
                    filtered.append(checklist)
            final_results += filtered
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


def lock_checklist_for_zaak(zaak: Zaak):
    checklist = fetch_checklist_object(zaak)
    if checklist:
        updated = False
        for answer in checklist["record"]["data"]["answers"]:
            if not answer["answer"] and (
                answer.get("userAssignee") or answer.get("groupAssignee")
            ):
                updated = True
                answer["userAssignee"] = None
                answer["groupAssignee"] = None
        checklist["record"]["data"]["locked"] = True

        if updated:
            update_object_record_data(
                object=checklist,
                data=camelize(
                    checklist["record"]["data"], **api_settings.JSON_UNDERSCOREIZE
                ),
            )


###################################################
#                Oudbehandelaren                  #
###################################################


@cache("fetch_oudbehandelaren_object:{zaak.url}", timeout=A_DAY)
def fetch_oudbehandelaren_object(zaak: Zaak) -> Optional[Dict]:
    oudbehandelaren = _search_meta_objects(
        "oudbehandelaren_objecttype", unique=True, zaak=zaak
    )
    if not oudbehandelaren:
        return None

    return oudbehandelaren[0]


def fetch_oudbehandelaren(zaak: Zaak) -> Optional[List[Oudbehandelaren]]:
    oudbehandelaren = fetch_oudbehandelaren_object(zaak)
    if not oudbehandelaren:
        return None

    return factory(Oudbehandelaren, oudbehandelaren["record"]["data"])


###################################################
#            KOWNSL - review requests             #
###################################################


def factory_review_request(data: Dict) -> ReviewRequest:
    rr = factory(ReviewRequest, data)
    # underscoreize in zgw_consumers.api_models.base.factory is messing
    # with the format of the keys in the user_deadlines dictionary
    rr.user_deadlines = data["userDeadlines"]
    return rr


def fetch_review_request(id: str) -> Optional[Dict]:
    data_attrs = [f"id__exact__{id}"]
    if objs := _search_meta_objects(
        "review_request_objecttype", data_attrs=data_attrs, unique=True
    ):

        return objs[0]
    return None


@cache("review_request:detail:{uuid}")
def get_review_request(uuid: str) -> Optional[ReviewRequest]:
    if obj := fetch_review_request(uuid):
        return factory_review_request(obj["record"]["data"])
    return None


@cache("review_requests:zaak:{zaak.uuid}")
def get_all_review_requests_for_zaak(zaak: Zaak) -> List[Optional[ReviewRequest]]:
    data_attrs = [f"zaak__exact__{zaak.url}"]
    if objs := _search_meta_objects("review_request_objecttype", data_attrs=data_attrs):
        review_requests = []
        for obj in objs:
            review_request = factory_review_request(obj["record"]["data"])
            review_request.zaak = zaak  # resolve zaak relation
            review_requests.append(review_request)
        return review_requests
    return []


def create_review_request(data: Dict) -> ReviewRequest:
    data["id"] = _create_unique_uuid_for_object(fetch_review_request)
    camelize_settings = api_settings.JSON_UNDERSCOREIZE
    camelize_settings["ignore_fields"] = (
        camelize_settings.get("ignore_fields") or []
    ) + ["user_deadlines"]
    result = create_meta_object_and_relate_to_zaak(
        "review_request", data, data["zaak"], camelize_settings=camelize_settings
    )
    return factory_review_request(result["record"]["data"])


def bulk_lock_review_requests_for_zaak(zaak: Zaak, reason: str = ""):
    def _lock_review_request(rr: ReviewRequest):
        return lock_review_request(
            str(rr.id),
            lock_reason=reason or "Verzoek is geannuleerd.",
        )

    review_requests = get_all_review_requests_for_zaak(zaak)
    review_requests = [rr for rr in review_requests if not rr.locked]
    with parallel(max_workers=settings.MAX_WORKERS) as executor:
        list(executor.map(_lock_review_request, review_requests))


def lock_review_request(
    uuid: str, lock_reason: str, requester: Optional[User] = None
) -> Optional[ReviewRequest]:
    if rr := fetch_review_request(uuid):  # Make sure it fetches uncached.
        rr["record"]["data"]["lockReason"] = lock_reason
        rr["record"]["data"]["locked"] = True
        result = update_object_record_data(rr, rr["record"]["data"], user=requester)
    else:
        raise Http404(
            _("Review request with id {uuid} does not exist.").format(uuid=uuid)
        )

    return factory_review_request(result["record"]["data"])


def update_review_request(
    uuid: str,
    requester: User,
    data: Dict = dict,
) -> Optional[ReviewRequest]:
    if rr := fetch_review_request(uuid):  # Make sure it fetches uncached.
        rr["record"]["data"] = {
            **rr["record"]["data"],
            **camelize(data, **api_settings.JSON_UNDERSCOREIZE),
        }
        result = update_object_record_data(rr, rr["record"]["data"], user=requester)
    else:
        raise Http404(
            _("Review request with id {uuid} does not exist.").format(uuid=uuid)
        )

    return factory_review_request(result["record"]["data"])


def get_review_requests_paginated(
    query_params: Optional[Dict] = None,
    zaak: Optional[Zaak] = None,
    requester: Optional[User] = None,
    not_locked: Optional[bool] = False,
    latest_version: Optional[bool] = True,
    page_size: int = 100,
) -> Tuple[List[Dict], Dict]:

    data_attrs = []

    if zaak:
        data_attrs += [f"zaak__exact__{zaak.url}"]
    if requester:
        data_attrs += [f"requester__username__exact__{requester.username}"]
    if not_locked:
        data_attrs += [f"locked__icontains__false"]
    if latest_version:
        future_date = datetime.date.today() + datetime.timedelta(
            days=100 * 365
        )  # 100 years lawl

    response, query_params = _search_meta_objects(
        "review_request_objecttype",
        data_attrs=data_attrs,
        extra_kwargs={"date": future_date.isoformat()} if latest_version else None,
        paginated=True,
        page_size=page_size,
        query_params=query_params,
    )
    review_requests = [
        factory_review_request(rr["record"]["data"]) for rr in response["results"]
    ]
    response["results"] = review_requests
    return response, query_params


def count_review_requests_by_user(requester: User) -> Optional[int]:
    response, query_params = get_review_requests_paginated(
        requester=requester, page_size=1, not_locked=True
    )
    return response.get("count", None)


###################################################
#                KOWNSL - reviews                 #
###################################################


def factory_reviews(data: Dict) -> Reviews:
    return factory(Reviews, data)


def fetch_review_on_id(id: str) -> Optional[Dict]:
    return fetch_reviews(id=id)


def fetch_reviews(
    review_request: Optional[str] = None,
    id: Optional[str] = None,
    zaak: Optional[str] = None,
    requester: Optional[User] = None,
) -> List[Dict]:

    data_attrs = []

    if review_request:
        data_attrs += [f"reviewRequest__exact__{review_request}"]
    if id:
        data_attrs += [f"id__exact__{id}"]
    if zaak:
        data_attrs += [f"zaak__exact__{zaak}"]
    if requester:
        data_attrs += [f"requester__exact__{requester.username}"]

    if objs := _search_meta_objects(
        "review_objecttype",
        data_attrs=data_attrs,
        unique=True if review_request or id else False,
    ):
        return objs

    return list()


@cache("reviews:zaak:{zaak.uuid}")
def get_reviews_for_zaak(zaak: Zaak) -> List[Reviews]:
    results = fetch_reviews(zaak=zaak.url)
    if results:
        reviews = []
        for rev in results:
            reviews.append(factory_reviews(rev["record"]["data"]))
        return reviews
    return list()


@cache("reviews:review_request:{review_request.id}")
def get_reviews_for_review_request(
    review_request: ReviewRequest,
) -> Optional[Reviews]:
    results = fetch_reviews(review_request=review_request.id)
    if results:
        return factory_reviews(results[0]["record"]["data"])
    return None


@cache("reviews:requester:{requester.username}")
def get_reviews_for_requester(
    requester: User,
) -> List[Reviews]:
    results = fetch_reviews(requester=requester)
    if results:
        reviews = []
        for rev in results:
            reviews.append(factory_reviews(rev["record"]["data"]))
        return reviews
    return list()


def create_reviews_for_review_request(
    data: Dict, review_request: ReviewRequest
) -> Reviews:
    object_data = {
        "zaak": review_request.zaak,
        "review_request": str(review_request.id),
        "review_type": review_request.review_type,
        "reviews": [data],
        "id": _create_unique_uuid_for_object(fetch_review_on_id),
        "requester": review_request.requester,
    }
    result = create_meta_object_and_relate_to_zaak(
        "review", object_data, review_request.zaak
    )
    return factory_reviews(result["record"]["data"])


def update_reviews_for_review_request(data: Dict, reviews_object: Dict) -> Reviews:
    reviews_object["record"]["data"]["reviews"].append(
        camelize(data, **api_settings.JSON_UNDERSCOREIZE)
    )
    result = update_object_record_data(reviews_object, reviews_object["record"]["data"])
    return factory_reviews(result["record"]["data"])


def submit_review(data: Dict, review_request: ReviewRequest) -> Reviews:
    results = fetch_reviews(review_request=str(review_request.id))
    if results:
        return update_reviews_for_review_request(data, results[0])

    return create_reviews_for_review_request(data, review_request)
