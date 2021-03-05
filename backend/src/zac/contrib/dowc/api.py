from typing import Dict, Optional, Tuple

from django.http import Http404

from furl import furl
from rest_framework import status
from zds_client.client import ClientError
from zds_client.schema import get_operation_url
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.documenten import Document

from zac.accounts.models import User
from zac.client import Client
from zac.utils.decorators import optional_service

from .data import DowcResponse
from .models import DowcConfig


def get_client(user: User) -> Client:
    config = DowcConfig.get_solo()
    assert config.service, "A service must be configured first"
    service = config.service

    # override the actual logged in user in the `user_id` claim, so that D.O.C. is
    # aware of the actual end user
    if user is not None:
        service.user_id = user.username
    client = service.build_client()
    client.operation_suffix_mapping = {
        **client.operation_suffix_mapping,
        "delete": "_destroy",
    }
    return client


@optional_service
def create_doc(
    user: User,
    document: Document,
    purpose: str,
    referer: str,
) -> Tuple[DowcResponse, int]:

    drc_url = furl(document.url).add({"versie": document.versie}).url
    client = get_client(user)
    try:
        response = client.create(
            "documenten",
            data={
                "drc_url": drc_url,
                "purpose": purpose,
                "info_url": referer,
            },
        )
        return factory(DowcResponse, response), status.HTTP_201_CREATED
    except ClientError:
        response = client.list(
            "documenten",
            query_params={
                "drc_url": drc_url,
                "purpose": purpose,
            },
        )
        return factory(DowcResponse, response[0]), status.HTTP_200_OK


@optional_service
def patch_and_destroy_doc(user: User, uuid: str) -> Dict[str, str]:
    client = get_client(user)
    operation_id = "documenten_destroy"
    try:
        url = get_operation_url(client.schema, operation_id, uuid=uuid)
        return client.request(url, operation_id, method="DELETE", expected_status=200)

    except ClientError:
        raise Http404(f"DocumentFile with id {uuid} does not exist.")
