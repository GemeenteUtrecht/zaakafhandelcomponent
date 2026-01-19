from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.utils.translation import gettext_lazy as _

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView

from zac.accounts.models import User
from zac.api.permissions import DefinitionBasePermission
from zac.camunda.constants import AssigneeTypeChoices
from zac.core.api.permissions import (
    BaseConditionalPermission,
    CanReadZaken,
    CanUpdateZaken,
)
from zac.core.camunda.utils import resolve_assignee
from zac.core.services import get_zaak

from .data import ReviewRequest


class CanReadZakenReviewRequests(CanReadZaken):
    def has_object_permission(self, request: Request, view: APIView, obj):
        if request.user.is_superuser:
            return True

        if isinstance(obj, ReviewRequest):
            try:
                obj = get_zaak(zaak_url=obj.zaak)
            except ObjectDoesNotExist:
                raise Http404(f"No ZAAK is found for url: {obj.zaak}.")

        permission_name = self.get_permission(request).name
        # first check atomic permissions - this checks both atomic permissions directly attached to the user
        # and atomic permissions defined to authorization profiles
        if self.user_atomic_permissions_exists(
            request, permission_name, obj_url=obj.url
        ):
            return True

        # then check blueprint permissions
        for permission in self.get_blueprint_permissions(request, permission_name):
            if permission.has_access(obj, request.user, permission_name):
                return True

        return False


class CanUpdateZakenReviewRequests(CanUpdateZaken):
    def has_object_permission(self, request: Request, view: APIView, obj):
        if request.user.is_superuser:
            return True

        if isinstance(obj, ReviewRequest):
            try:
                obj = get_zaak(zaak_url=obj.zaak)
            except ObjectDoesNotExist:
                raise Http404(f"No ZAAK is found for url: {obj.zaak}.")

        permission_name = self.get_permission(request).name
        # first check atomic permissions - this checks both atomic permissions directly attached to the user
        # and atomic permissions defined to authorization profiles
        if self.user_atomic_permissions_exists(
            request, permission_name, obj_url=obj.url
        ):
            return True

        # then check blueprint permissions
        for permission in self.get_blueprint_permissions(request, permission_name):
            if permission.has_access(obj, request.user, permission_name):
                return True

        return False


class CanReadOrUpdateReviews(BaseConditionalPermission):
    def get_permission(self, request) -> DefinitionBasePermission:
        if request.method in permissions.SAFE_METHODS:
            return CanReadZakenReviewRequests()
        else:
            return CanUpdateZakenReviewRequests()


class ReviewIsUnlocked(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method not in permissions.SAFE_METHODS and isinstance(
            obj, ReviewRequest
        ):
            requester = obj.requester["full_name"] or obj.requester["username"]
            self.message = _("Review request is locked by `{requester}`.").format(
                requester=requester
            )
            return not obj.locked
        return True


class ReviewIsNotBeingReconfigured(permissions.BasePermission):
    message = _("This review request is being reconfigured.")

    def has_object_permission(self, request, view, obj):
        if request.method not in permissions.SAFE_METHODS and isinstance(
            obj, ReviewRequest
        ):
            return not obj.is_being_reconfigured
        return True


class IsReviewUser(permissions.BasePermission):
    message = _("This user is not a reviewer.")

    def has_object_permission(self, request, view, obj):
        assignees = [
            f"{AssigneeTypeChoices.group}:{group}"
            for group in request.user.groups.all()
        ]
        assignees.append(f"{AssigneeTypeChoices.user}:{request.user}")
        return any([assignee in obj.user_deadlines for assignee in assignees])


class IsReviewRequester(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.requester["username"] == request.user.username


class HasNotReviewed(permissions.BasePermission):
    _message = _(
        "This request is already handled by `{assignee}` from within {identificatie}."
    )

    def has_object_permission(self, request, view, obj):
        assignee = resolve_assignee(request.query_params.get("assignee"))
        zaak = get_zaak(zaak_url=obj.zaak)
        reviews = obj.get_reviews()

        assignee_is_user = isinstance(assignee, User)
        for review in reviews:
            if review.group:
                if assignee_is_user:
                    continue

                if assignee.name == review.group.get("name"):
                    self.message = self._message.format(
                        assignee=assignee.name, identificatie=zaak.identificatie
                    )
                    return False
            else:
                if not assignee_is_user:
                    continue

                if assignee.username == review.author["username"]:
                    self.message = self._message.format(
                        assignee=assignee.get_full_name(),
                        identificatie=zaak.identificatie,
                    )
                    return False
        return True
