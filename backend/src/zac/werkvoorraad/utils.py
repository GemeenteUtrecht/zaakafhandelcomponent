import logging
from itertools import groupby
from typing import Dict, List
from urllib.request import Request

from zgw_consumers.api_models.base import factory

from zac.accounts.models import AccessRequest, User
from zac.contrib.kownsl.api import get_client as get_kownsl_client
from zac.contrib.kownsl.data import ReviewRequest
from zac.core.permissions import zaken_handle_access
from zac.elasticsearch.searches import search_zaken

from .data import ActivityGroup, ChecklistAnswerGroup

logger = logging.getLogger(__name__)


def get_access_requests(request: Request, zaken):
    if not request.user.has_perm(zaken_handle_access.name):
        return []

    return AccessRequest.objects.filter(result="", zaak__in=list(zaken.keys()))


def count_access_requests(request: Request) -> int:
    behandelaar_zaken = {
        zaak.url: zaak
        for zaak in search_zaken(request=request, behandelaar=request.user.username)
    }
    if not behandelaar_zaken:
        return 0
    return get_access_requests(request, behandelaar_zaken).count()


def get_access_requests_groups(request: Request) -> List[dict]:
    behandelaar_zaken = {
        zaak.url: zaak
        for zaak in search_zaken(request=request, behandelaar=request.user.username)
    }
    if not behandelaar_zaken:
        return []

    # if user doesn't have a permission to handle access requests - don't show them
    qs = get_access_requests(request, zaken=behandelaar_zaken).order_by(
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


def filter_on_existing_zaken(request: Request, groups: List[Dict]) -> List[Dict]:
    zaak_urls = list({group["zaak_url"] for group in groups})
    es_results = search_zaken(request=request, urls=zaak_urls, size=len(zaak_urls))
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


def get_review_requests_for_requester(user: User) -> List[ReviewRequest]:
    client = get_kownsl_client()
    results = client.list("review_requests", query_params={"requester": user.username})
    review_requests = factory(ReviewRequest, results)

    # fix relation reference
    for result, review_request in zip(results, review_requests):
        review_request.user_deadlines = result["userDeadlines"]
    return review_requests
