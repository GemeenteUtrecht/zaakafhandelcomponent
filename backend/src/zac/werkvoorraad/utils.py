import logging
from itertools import groupby
from typing import Dict, List
from urllib.request import Request

from zac.accounts.models import AccessRequest
from zac.core.permissions import zaken_handle_access
from zac.elasticsearch.searches import search_zaken

from .data import ActivityGroup, ChecklistAnswerGroup

logger = logging.getLogger(__name__)


def get_access_requests(request: Request, zaken: List[str]):
    if not request.user.has_perm(zaken_handle_access.name):
        return []

    return AccessRequest.objects.filter(result="", zaak__in=zaken)


def count_access_requests(request: Request) -> int:
    behandelaar_zaken = {
        zaak.url
        for zaak in search_zaken(
            request=request, behandelaar=request.user.username, fields=["url"], size=500
        )
    }
    if not behandelaar_zaken:
        return 0
    return get_access_requests(request, list(behandelaar_zaken)).count()


def get_access_requests_groups(request: Request) -> List[dict]:
    behandelaar_zaken = {
        zaak.url: zaak
        for zaak in search_zaken(
            request=request,
            behandelaar=request.user.username,
            fields=[
                "url",
                "identificatie",
                "bronorganisatie",
                "status",
                "zaaktype",
                "omschrijving",
                "deadline",
            ],
            size=500,
        )
    }
    if not behandelaar_zaken:
        return []

    # if user doesn't have a permission to handle access requests - don't show them
    qs = get_access_requests(request, zaken=list(behandelaar_zaken.keys())).order_by(
        "zaak", "requester__username"
    )
    requested_zaken = []
    for zaak_url, group in groupby(qs, key=lambda a: a.zaak):
        requested_zaken.append(
            {
                "zaak_url": zaak_url,
                "access_requests": list(group),
                "zaak": behandelaar_zaken[zaak_url],
            }
        )
    return requested_zaken


def filter_on_existing_zaken(
    request: Request, groups: List[Dict], **kwargs
) -> List[Dict]:
    zaak_urls = list({group["zaak_url"] for group in groups})
    es_results = search_zaken(
        request=request, urls=zaak_urls, size=len(zaak_urls), **kwargs
    )
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
    activity_groups_with_zaak = filter_on_existing_zaken(
        request, grouped_activities, only_allowed=False
    )
    return [ActivityGroup(**group) for group in activity_groups_with_zaak]


def get_checklist_answers_groups(
    request: Request, grouped_checklist_answers: List[dict]
) -> List[ChecklistAnswerGroup]:
    checklist_answers_groups_with_zaak = filter_on_existing_zaken(
        request, grouped_checklist_answers, only_allowed=False
    )
    return [
        ChecklistAnswerGroup(**group) for group in checklist_answers_groups_with_zaak
    ]
