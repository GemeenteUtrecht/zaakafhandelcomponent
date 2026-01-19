from django.urls import path

from .views import (
    WorkStackAccessRequestsView,
    WorkStackAdhocActivitiesView,
    WorkStackAssigneeCasesView,
    WorkStackChecklistQuestionsView,
    WorkStackGroupAdhocActivitiesView,
    WorkStackGroupChecklistQuestionsView,
    WorkStackGroupTasksView,
    WorkStackReviewRequestsView,
    WorkStackSummaryView,
    WorkStackUserTasksView,
)

app_name = "werkvoorraad"

urlpatterns = [
    path("cases", WorkStackAssigneeCasesView.as_view(), name="cases"),
    path("activities", WorkStackAdhocActivitiesView.as_view(), name="activities"),
    path(
        "group-activities",
        WorkStackGroupAdhocActivitiesView.as_view(),
        name="group-activities",
    ),
    path("user-tasks", WorkStackUserTasksView.as_view(), name="user-tasks"),
    path("group-tasks", WorkStackGroupTasksView.as_view(), name="group-tasks"),
    path(
        "access-requests",
        WorkStackAccessRequestsView.as_view(),
        name="access-requests",
    ),
    path("checklists", WorkStackChecklistQuestionsView.as_view(), name="checklists"),
    path(
        "group-checklists",
        WorkStackGroupChecklistQuestionsView.as_view(),
        name="group-checklists",
    ),
    path(
        "review-requests", WorkStackReviewRequestsView.as_view(), name="review-requests"
    ),
    path("summary", WorkStackSummaryView.as_view(), name="summary"),
]
