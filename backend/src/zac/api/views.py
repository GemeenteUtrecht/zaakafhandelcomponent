from django.http import HttpResponse

import requests

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
