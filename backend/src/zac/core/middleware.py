"""
Read-only mode middleware.

When ``CoreConfig.read_only_mode`` is enabled (Django admin -> Core > Global
configuration), all write requests (anything other than GET/HEAD/OPTIONS) to
``/api/`` are blocked with a 503, except for a fixed allowlist of endpoints
that are required to keep the system usable while in read-only mode:

- session/account management endpoints (logout, access requests, auth
  profiles, groups, roles, user-auth-profiles, atomic case permissions),
- the "management" sub-apps (accounts, core, checklists, search), which are
  operational/config endpoints rather than primary-data mutations,
- the activities app,
- endpoints that are functionally read-only queries but exposed over a
  non-GET HTTP verb (e.g. search/filter endpoints that take a request body).

Non-API paths (Django admin, OIDC, static/media, ...) are never touched, so
the admin panel always stays reachable to toggle the flag back off.

The middleware is placed early in the MIDDLEWARE stack (right after
CorsMiddleware) so blocked requests are rejected before session, auth and CSRF
processing kick in - this keeps rejection cheap under a high volume of writes.
"""

import re
from typing import Optional, Pattern, Set, Tuple

from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _

from .models import read_only_mode_enabled

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

# path segment placeholder, e.g. an id/uuid/bronorganisatie/identificatie
_ID = r"[^/]+"

# (allowed HTTP methods or None for "any method", regex matched against request.path)
_EXEMPT_RULES: Tuple[Tuple[Optional[Set[str]], str], ...] = (
    # accounts: access requests, auth profiles, groups, roles, user-auth-profiles
    ({"PATCH"}, rf"^/api/accounts/access-requests/{_ID}$"),
    ({"POST"}, r"^/api/accounts/auth-profiles$"),
    ({"PUT", "DELETE"}, rf"^/api/accounts/auth-profiles/{_ID}$"),
    ({"POST"}, r"^/api/accounts/cases/access$"),
    ({"DELETE"}, rf"^/api/accounts/cases/access/{_ID}$"),
    ({"PUT"}, r"^/api/accounts/cases/access/bulk_update$"),
    ({"POST"}, r"^/api/accounts/groups$"),
    ({"PUT", "DELETE"}, rf"^/api/accounts/groups/{_ID}$"),
    ({"POST"}, r"^/api/accounts/logout$"),
    ({"POST"}, r"^/api/accounts/roles$"),
    ({"PUT", "PATCH", "DELETE"}, rf"^/api/accounts/roles/{_ID}$"),
    ({"POST"}, r"^/api/accounts/user-auth-profiles$"),
    ({"PUT", "PATCH", "DELETE"}, rf"^/api/accounts/user-auth-profiles/{_ID}$"),
    # "management" sub-apps (drf-spectacular schema tag "management"): any method
    (None, r"^/api/accounts/management/"),
    (None, r"^/api/core/management/"),
    (None, r"^/api/checklists/management/"),
    (None, r"^/api/search/management/"),
    # activities app: any method
    (None, r"^/api/activities/"),
    # read-like endpoints exposed over a non-GET HTTP verb
    ({"PATCH"}, r"^/api/core/recently-viewed$"),
    ({"POST"}, r"^/api/core/rollen/medewerker/betrokkeneIdentificatie$"),
    ({"POST"}, r"^/api/dashboard/management$"),
    ({"POST"}, r"^/api/dashboard/management/summary$"),
    ({"POST"}, r"^/api/core/objects$"),
    ({"POST"}, rf"^/api/search/cases/{_ID}/{_ID}/documents$"),
    ({"POST"}, r"^/api/search/quick-search$"),
    ({"POST"}, r"^/api/search/reports/$"),
    ({"PUT", "PATCH", "DELETE"}, rf"^/api/search/reports/{_ID}/$"),
    ({"POST"}, r"^/api/search/vgu-reports/informatieobjecten$"),
    ({"POST"}, r"^/api/search/vgu-reports/zaken$"),
    ({"POST"}, r"^/api/search/zaken$"),
    ({"POST"}, r"^/api/workstack/summary$"),
)

_COMPILED_EXEMPT_RULES: Tuple[Tuple[Optional[Set[str]], Pattern], ...] = tuple(
    (methods, re.compile(pattern)) for methods, pattern in _EXEMPT_RULES
)


def _is_exempt(method: str, path: str) -> bool:
    for methods, pattern in _COMPILED_EXEMPT_RULES:
        if methods is not None and method not in methods:
            continue
        if pattern.match(path):
            return True
    return False


READ_ONLY_MODE_MESSAGE = _(
    "LET OP: SYSTEEM STAAT OP ENKEL LEZEN. ER KUNNEN GEEN WIJZIGINGEN WORDEN "
    "AANGEBRACHT."
)


class ReadOnlyModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.method not in SAFE_METHODS
            and request.path.startswith("/api/")
            and read_only_mode_enabled()
            and not _is_exempt(request.method, request.path)
        ):
            return JsonResponse({"detail": str(READ_ONLY_MODE_MESSAGE)}, status=503)

        return self.get_response(request)
