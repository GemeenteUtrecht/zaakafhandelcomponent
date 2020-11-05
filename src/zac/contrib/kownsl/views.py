from zac.notifications.views import NotificationCallbackView


class KownslNotificationCallbackView(NotificationCallbackView):
    def handle_notification(self, data: dict):
        # just to make sure, shouldn't happen with our URL routing
        if not data["kanaal"] == "kownsl":
            return

        import bpdb

        bpdb.set_trace()
