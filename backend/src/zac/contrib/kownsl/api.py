from typing import Dict, List, Optional, Tuple

from django.http import Http404
from django.utils.translation import gettext_lazy as _

from zds_client.client import ClientError
from zgw_consumers.api_models.base import factory
from zgw_consumers.client import ZGWClient

from zac.accounts.models import User
from zac.core.utils import fetch_next_url_pagination
from zac.utils.decorators import cache, optional_service
from zgw.models.zrc import Zaak

from .data import Advice, Approval, ReviewRequest
from .models import KownslConfig


def get_client(user: Optional[User] = None) -> ZGWClient:
    config = KownslConfig.get_solo()
    assert config.service, "A service must be configured first"
    service = config.service

    # override the actual logged in user in the `user_id` claim, so that Kownsl is
    # aware of the actual end user
    if user is not None:
        service.user_id = user.username
    client = service.build_client()
    client.operation_suffix_mapping = {
        **client.operation_suffix_mapping,
        "retrieve": "_retrieve",
    }
    return client


def create_review_request(
    zaak_url: str,
    requester: User,
    documents: List[str],
    review_type: str = "advice",
    toelichting: str = "",
    assigned_users: Optional[dict] = None,
) -> ReviewRequest:
    client = get_client(user=requester)
    data = {
        "for_zaak": zaak_url,
        "review_type": review_type,
        "documents": documents,
        "toelichting": toelichting,
        "assigned_users": assigned_users,
    }
    result = client.create("review_requests", data=data)
    rr = factory(ReviewRequest, result)

    # underscoreize in zgw_consumers.api_models.base.factory is messing
    # with the format of the keys in the user_deadlines dictionary
    rr.user_deadlines = result["userDeadlines"]
    return rr


@optional_service
@cache("reviewrequest:advices:{review_request.id}")
def retrieve_advices(review_request: ReviewRequest) -> List[Advice]:
    """
    Retrieve the advices for a single review request.

    :param review_request_uuid: uuid of review request in Kownsl API
    :return: an list of advice object
    """
    client = get_client()
    result = client.list("review_requests_advices", request__uuid=review_request.id)
    return factory(Advice, result)


@optional_service
@cache("reviewrequest:approvals:{review_request.id}")
def retrieve_approvals(review_request: ReviewRequest) -> List[Approval]:
    """
    Retrieve the approvals for a single review request.

    :param review_request_uuid: uuid of review request in Kownsl API
    :return: an approval-collection object
    """
    client = get_client()
    result = client.list("review_requests_approvals", request__uuid=review_request.id)
    return factory(Approval, result)


@optional_service
@cache("reviewrequest:detail:{uuid}")
def get_review_request(uuid: str) -> Optional[ReviewRequest]:
    client = get_client()
    # Reviewrequest_retrieve translates to reviewrequest_read which isn't a valid
    # operation_id in the schema (yet?). Building the url and doing the request
    # manually for now.
    try:
        result = client.retrieve("review_requests", uuid=uuid)
    except ClientError:
        raise Http404(f"Review request with id {uuid} does not exist.")

    review_request = factory(ReviewRequest, result)

    # underscoreize in zgw_consumers.api_models.base.factory is messing
    # with the format of the keys in the user_deadlines dictionary
    review_request.user_deadlines = result["userDeadlines"]
    return review_request


@optional_service
def get_review_requests_paginated(
    query_params: Optional[Dict] = None,
    zaak: Optional[Zaak] = None,
    requester: Optional[User] = None,
) -> Tuple[List[Dict], Dict]:
    client = get_client()

    if not query_params:
        query_params = {}

    if zaak:
        query_params["for_zaak"] = zaak.url
    if requester:
        query_params["requester"] = requester.username

    results = client.list("review_requests", query_params=query_params)
    review_requests = factory(ReviewRequest, results["results"])
    # fix relation reference
    for result, review_request in zip(results["results"], review_requests):
        review_request.user_deadlines = result["userDeadlines"]
    results["results"] = review_requests
    query_params = fetch_next_url_pagination(results, query_params=query_params)
    return results, query_params


@optional_service
@cache("reviewrequests:zaak:{zaak.uuid}")
def get_all_review_requests_for_zaak(zaak: Zaak) -> List[ReviewRequest]:
    get_more = True
    query_params = {}
    results = []
    while get_more:
        rrs, query_params = get_review_requests_paginated(
            query_params=query_params, zaak=zaak
        )
        results += rrs["results"]
        get_more = query_params.get("page", None)

    # fix relation reference
    for review_request in results:
        review_request.for_zaak = zaak
    return results


@optional_service
def lock_review_request(uuid: str, lock_reason: str) -> Optional[ReviewRequest]:
    client = get_client()
    try:
        result = client.partial_update(
            "review_requests",
            uuid=uuid,
            data={"lock_reason": lock_reason, "locked": True},
        )
    except ClientError:
        raise Http404(
            _("Review request with id {uuid} does not exist.").format(uuid=uuid)
        )

    review_request = factory(ReviewRequest, result)
    review_request.user_deadlines = result["userDeadlines"]
    return review_request


@optional_service
def update_assigned_users_review_request(
    uuid: str,
    requester: User,
    data: Dict = dict,
) -> Optional[ReviewRequest]:

    client = get_client(user=requester)
    try:
        result = client.partial_update(
            "review_requests",
            uuid=uuid,
            data=data,
        )
    except ClientError:
        raise Http404(
            _("Review request with id {uuid} does not exist.").format(uuid=uuid)
        )

    review_request = factory(ReviewRequest, result)
    review_request.user_deadlines = result["userDeadlines"]
    return review_request
