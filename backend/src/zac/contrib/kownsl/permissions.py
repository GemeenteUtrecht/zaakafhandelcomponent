from django.utils.translation import gettext_lazy as _

from rest_framework import permissions
from zgw_consumers.api_models.base import factory

from zac.camunda.constants import AssigneeTypeChoices
from zac.core.camunda.utils import resolve_assignee
from zac.core.services import get_zaak

from .api import retrieve_advices, retrieve_approvals
from .constants import KownslTypes
from .data import ReviewRequest


class IsReviewUser(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        assignees = [
            f"{AssigneeTypeChoices.group}:{group}"
            for group in request.user.groups.all()
        ]
        assignees.append(f"{AssigneeTypeChoices.user}:{request.user.username}")
        return any([assignee in obj["userDeadlines"] for assignee in assignees])


class HasNotReviewed(permissions.BasePermission):
    _message = _(
        "This request is already handled by assignee `{assignee}` from within ZAAK {identificatie}."
    )

    def has_object_permission(self, request, view, obj):
        assignee = resolve_assignee(request.query_params.get("assignee"))
        rr = factory(ReviewRequest, obj)
        zaak = get_zaak(zaak_url=rr.for_zaak)
        if rr.review_type == KownslTypes.advice:
            reviews = retrieve_advices(rr)
        else:
            reviews = retrieve_approvals(rr)

        for review in reviews:
            if review.group:
                if assignee.name == review.group:
                    self.message = self._message.format(
                        assignee=assignee.name, identificatie=zaak.identificatie
                    )
                    return False
            else:
                if assignee.username == review.author.username:
                    self.message = self._message.format(
                        assignee=assignee.get_full_name(),
                        identificatie=zaak.identificatie,
                    )
                    return False
        return True
