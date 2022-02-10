from django.utils.translation import gettext_lazy as _

from rest_framework import permissions
from zgw_consumers.api_models.base import factory

from zac.camunda.constants import AssigneeTypeChoices
from zac.core.camunda.utils import resolve_assignee

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
    _message = _("Review for review request `%s` is already given by assignee(s) `%s`.")

    def has_object_permission(self, request, view, obj):
        assignee = resolve_assignee(request.query_params.get("assignee"))
        rr = factory(ReviewRequest, obj)
        if rr.review_type == KownslTypes.advice:
            reviews = retrieve_advices(rr)
        else:
            reviews = retrieve_approvals(rr)

        for review in reviews:
            if review.group:
                if assignee.name == review.group:
                    self.message = self._message % (rr.id, assignee.name)
                    return False
            else:
                if assignee.username == review.author.username:
                    self.message = self._message % (rr.id, assignee.get_full_name())
                    return False
        return True
