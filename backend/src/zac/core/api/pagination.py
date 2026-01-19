from collections import OrderedDict

from django.utils.translation import gettext_lazy as _

from furl import furl
from rest_framework.pagination import PageNumberPagination, _positive_int
from rest_framework.response import Response
from rest_framework.views import APIView


class BffPagination(PageNumberPagination):
    """
    Allows users to define page size in the view.

    """

    page_size_query_param = "pageSize"
    page_query_param = "page"
    page_size = 100

    def get_page_size(self, request):
        if self.page_size_query_param:
            try:
                return _positive_int(
                    request.query_params[self.page_size_query_param],
                    strict=True,
                    cutoff=self.max_page_size,
                )
            except (KeyError, ValueError):
                pass

        view = request.resolver_match.func.cls
        if (
            callable(view)
            and isinstance(view(), APIView)
            and (page_size := getattr(view, "page_size", None))
        ):
            return page_size

        return self.page_size


class ProxyPagination(BffPagination):
    """
    This assumes data coming in is already paginated.
    It basically alters the URLs so that ZAC will proxy the correct calls
    without exposing the end-application.

    """

    page_size = 20

    def get_next_link(self, request, data):
        if not data["next"]:
            return None
        return furl(request.build_absolute_uri()).set(furl(data["next"]).args).url

    def get_previous_link(self, request, data):
        if not data["previous"]:
            return None
        return furl(request.build_absolute_uri()).set(furl(data["previous"]).args).url

    def get_paginated_response(self, request, data):
        return Response(
            OrderedDict(
                [
                    ("count", data["count"]),
                    ("next", self.get_next_link(request, data)),
                    ("previous", self.get_previous_link(request, data)),
                    ("results", data["results"]),
                ]
            )
        )
