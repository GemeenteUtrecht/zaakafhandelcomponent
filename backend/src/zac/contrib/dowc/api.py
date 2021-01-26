from typing import Dict, Optional, Tuple

from rest_framework import status
from zds_client.schema import get_operation_url
from zgw_consumers.api_models.base import factory
from zgw_consumers.client import ZGWClient

from zac.accounts.models import User
from zac.utils.decorators import optional_service

from .data import DowcResponse
from .models import DowcConfig


def get_client(user: User) -> ZGWClient:
    config = DowcConfig.get_solo()
    assert config.service, "A service must be configured first"
    service = config.service

    # override the actual logged in user in the `user_id` claim, so that D.O.C. is
    # aware of the actual end user
    if user is not None:
        service.user_id = user.username
    return service.build_client()


@optional_service
def get_doc_info(user: User, drc_url: str, purpose: str) -> Optional[Tuple[DowcResponse, int]]:
    client = get_client(user)
    try:
        response = client.create(
            "v1_documenten",
            data={
                "drc_url": drc_url,
                "purpose": purpose,
            },
        )
        return factory(DowcResponse, response), status.HTTP_201_CREATED
    except AssertionError:
        response = client.list(
            "v1_documenten",
            query_params={
                "drc_url": drc_url,
                "purpose": purpose,
            },
        )
        return factory(DowcResponse, response[0]), status.HTTP_200_OK


@optional_service
def patch_and_destroy_doc(user: User, uuid: str) -> Dict:
    client = get_client(user)
    response = client.delete(
        "v1_documenten",
        uuid=uuid,
    )
    return response
