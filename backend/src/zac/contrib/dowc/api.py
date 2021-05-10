from typing import Dict, Tuple

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
from .exceptions import DOWCCreateError
from .models import DowcConfig


def get_client(user: User) -> Client:
    config = DowcConfig.get_solo()
    assert config.service, "A service must be configured first"
    service = config.service

    # override the actual logged in user in the `user_id` claim, so that Do.W.C. is
    # aware of the actual end user
    claims = {}
    if user is not None:
        service.user_id = user.username
        claims["email"] = user.email

    client = service.build_client(**claims)
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

    data = {"drc_url": drc_url, "purpose": purpose, "info_url": referer}
    try:  # First try to create the object in dowc
        response = client.create("documenten", data=data)
        status_code = status.HTTP_201_CREATED

    except ClientError as err:
        if err.args == (
            None,
        ):  # Requesting user may already have created an object dowc
            try:
                # We can fetch the first from the list because the
                # client will have raised an exception
                # if the status isn't as expected.
                response = client.list("documenten", data=data)[0]
                status_code = status.HTTP_200_OK
            except ClientError as err:  # Relay error
                raise DOWCCreateError(err.args[0])

        else:  # Object might exist and is owned by a different user
            raise DOWCCreateError(err.args[0])

    return factory(DowcResponse, response), status_code


@optional_service
def patch_and_destroy_doc(user: User, uuid: str) -> Dict[str, str]:
    client = get_client(user)
    operation_id = "documenten_destroy"
    try:
        url = get_operation_url(client.schema, operation_id, uuid=uuid)
        return client.request(url, operation_id, method="DELETE", expected_status=200)

    except ClientError:
        raise Http404(f"DocumentFile with id {uuid} does not exist.")
