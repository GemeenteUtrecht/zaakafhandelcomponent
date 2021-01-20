from typing import Dict

from zgw_consumers.api_models.base import factory
from zgw_consumers.client import ZGWClient

from zac.accounts.models import User
from zac.utils.decorators import optional_service

from .data import DocRequest
from .models import DocConfig


def get_client(user: User) -> ZGWClient:
    config = DocConfig.get_solo()
    assert config.service, "A service must be configured first"
    service = config.service

    # override the actual logged in user in the `user_id` claim, so that D.O.C. is
    # aware of the actual end user
    if user is not None:
        service.user_id = user.username
    return service.build_client()


@optional_service
def get_document(user: User, drc_url: str, purpose: str) -> DocRequest:
    client = get_client(user)
    operation_id = "v1_documenten_create"
    url = client.get_operation_url(client.schema, operation_id)
    response = client.request(
        url,
        operation_id,
        request_kwargs={
            "drc_url": drc_url,
            "purpose": purpose,
        },
    )
    return factory(DocRequest, response)


@optional_service
def delete_document(user: User, uuid: str) -> Dict:
    client = get_client(user)
    operation_id = "v1_documenten_destroy"
    url = client.get_operation_url(client.schema, operation_id, uuid=uuid)
    response = client.request(
        url,
        operation_id,
    )
    return response
