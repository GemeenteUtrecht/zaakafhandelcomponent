from rest_framework import permissions


class IsReviewUser(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        username = request.user.username
        return username in obj["userDeadlines"]
