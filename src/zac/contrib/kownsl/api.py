from typing import List, Union

from zds_client.client import get_operation_url
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.zaken import Zaak
from zgw_consumers.client import ZGWClient

from zac.utils.decorators import optional_service

from .data import Advice, Approval, ReviewRequest
from .models import KownslConfig


def factory_with_data(model: type, data: Union[dict, list]) -> Union[type, List[type]]:
    instances = factory(model, data)

    if isinstance(instances, list):
        for instance, data_instance in zip(instances, data):
            instance._data = data_instance
    else:
        instances._data = data
    return instances


def get_client() -> ZGWClient:
    config = KownslConfig.get_solo()
    assert config.service, "A service must be configured first"
    return config.service.build_client()


def create_review_request(
    zaak_url: str, review_type: str = "advice", num_assigned_users: int = 0
) -> ReviewRequest:
    client = get_client()
    data = {
        "for_zaak": zaak_url,
        "review_type": review_type,
        "num_assigned_users": num_assigned_users,
    }
    resp = client.create("reviewrequest", data=data)
    return factory(ReviewRequest, resp)


@optional_service
def retrieve_advices(review_request: ReviewRequest) -> List[Advice]:
    """
    Retrieve the advices for a single review request.

    :param review_request_uuid: uuid of review request in Kownsl API
    :return: an list of advice object
    """
    client = get_client()
    operation_id = "reviewrequest_advices"
    url = get_operation_url(client.schema, operation_id, uuid=review_request.id)
    result = client.request(url, operation_id)
    return factory_with_data(Advice, result)


@optional_service
def retrieve_approvals(review_request: ReviewRequest) -> List[Approval]:
    """
    Retrieve the approvals for a single review request.

    :param review_request_uuid: uuid of review request in Kownsl API
    :return: an approval-collection object
    """
    client = get_client()
    operation_id = "reviewrequest_approvals"
    url = get_operation_url(client.schema, operation_id, uuid=review_request.id)
    result = client.request(url, operation_id)
    return factory_with_data(Approval, result)


@optional_service
def get_review_requests(zaak: Zaak) -> List[ReviewRequest]:
    client = get_client()
    result = client.list("reviewrequest", query_params={"for_zaak": zaak.url})
    review_requests = factory_with_data(ReviewRequest, result)

    # fix relation reference
    for review_request in review_requests:
        review_request.for_zaak = zaak
    return review_requests
