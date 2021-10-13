from rest_framework import permissions

from zac.camunda.constants import AssigneeTypeChoices


class IsReviewUser(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        assignees = [
            f"{AssigneeTypeChoices.group}:{group}"
            for group in request.user.groups.all()
        ]
        assignees.append(f"user:{request.user.username}")
        return any([assignee in obj["assigneeDeadlines"] for assignee in assignees])
