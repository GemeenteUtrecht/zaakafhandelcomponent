import logging

from django_camunda.api import complete_task
from django_camunda.client import get_client as get_camunda_client
from zgw_consumers.models import Service

from zac.notifications.views import BaseNotificationCallbackView

logger = logging.getLogger(__name__)


class KownslNotificationCallbackView(BaseNotificationCallbackView):
    def handle_notification(self, data: dict):
        # just to make sure, shouldn't happen with our URL routing
        if not data["kanaal"] == "kownsl":
            return

        if data["actie"] == "reviewSubmitted":
            self._handle_review_submitted(data)

    @staticmethod
    def _handle_review_submitted(data: dict):
        client = Service.get_client(data["hoofd_object"])

        logger.debug("Retrieving review request %s", data["hoofd_object"])
        review_request = client.retrieve("reviewrequest", url=data["hoofd_object"])

        # look up and complete the user task in Camunda
        assignee = data["kenmerken"]["author"]
        camunda_client = get_camunda_client()

        params = {
            "processInstanceId": review_request["metadata"]["processInstanceId"],
            "taskDefinitionKey": review_request["metadata"]["taskDefinitionId"],
            "assignee": assignee,
        }
        logger.debug("Finding user tasks matching %r", params)
        tasks = camunda_client.get("task", params)

        if not tasks:
            logger.info(
                "No user tasks found - possibly they were already marked completed."
            )
            return

        if len(tasks) > 1:
            logger.warning(
                "Multiple user tasks with the same assignee and definition found in a single process instance!",
                extra={"tasks": tasks, "params": params},
            )

        for task in tasks:
            complete_task(task["id"], variables={})
