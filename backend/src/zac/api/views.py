from django.http import HttpResponse

import requests
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

HEADERS_TO_KEEP = (
    "api-version",
    "content-type",
    "x-oas-version",
)


def remote_schema_view(request):
    schema_url = request.GET["schema"]
    # TODO: cache
    response = requests.get(schema_url)

    django_response = HttpResponse(content=response.content)
    for header, value in response.headers.items():
        if header.lower() not in HEADERS_TO_KEEP:
            continue
        django_response[header] = value
    return django_response


@api_view()
@permission_classes(())
def health_check(request: Request):
    return Response({"healty": True})
