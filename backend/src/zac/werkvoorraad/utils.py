import logging
from itertools import groupby
from typing import Dict, List
from urllib.request import Request

from zac.accounts.models import AccessRequest
from zac.core.permissions import zaken_handle_access
from zac.elasticsearch.searches import search_zaken

from .data import ActivityGroup, ChecklistAnswerGroup

logger = logging.getLogger(__name__)


def get_access_requests_groups(request: Request):
    # if user doesn't have a permission to handle access requests - don't show them
    if not request.user.has_perm(zaken_handle_access.name):
        return []

    behandelaar_zaken = {
        zaak.url: zaak
        for zaak in search_zaken(request=request, behandelaar=request.user.username)
    }
    access_requests = AccessRequest.objects.filter(
        result="", zaak__in=list(behandelaar_zaken.keys())
    ).order_by("zaak", "requester__username")

    requested_zaken = []
    for zaak_url, group in groupby(access_requests, key=lambda a: a.zaak):
        requested_zaken.append(
            {
                "zaak_url": zaak_url,
                "access_requests": list(group),
                "zaak": behandelaar_zaken[zaak_url],
            }
        )
    return requested_zaken


def filter_on_existing_zaken(request: Request, groups: List[Dict]) -> List[Dict]:
    zaak_urls = list({group["zaak_url"] for group in groups})
    es_results = search_zaken(request=request, urls=zaak_urls)
    zaken = {zaak.url: zaak for zaak in es_results}

    # Make sure groups without a zaak in elasticsearch are not returned.
    filtered = []
    for group in groups:
        zaak = zaken.get(group["zaak_url"])
        if not zaak:
            logger.warning(
                "Can't find a zaak for url %s in elastic search." % group["zaak_url"]
            )
            continue

        group["zaak"] = zaak
        filtered.append(group)

    return filtered


def get_activity_groups(
    request: Request, grouped_activities: dict
) -> List[ActivityGroup]:
    activity_groups_with_zaak = filter_on_existing_zaken(request, grouped_activities)
    return [ActivityGroup(**group) for group in activity_groups_with_zaak]


def get_checklist_answers_groups(
    request: Request, grouped_checklist_answers: List[dict]
) -> List[ChecklistAnswerGroup]:
    checklist_answers_groups_with_zaak = filter_on_existing_zaken(
        request, grouped_checklist_answers
    )
    return [
        ChecklistAnswerGroup(**group) for group in checklist_answers_groups_with_zaak
    ]
