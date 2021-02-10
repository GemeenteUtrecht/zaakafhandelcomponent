from zac.api.permissions import RulesPermission
from zac.core.permissions import zaakproces_send_message, zaakproces_usertasks


class CanPerformTasks(RulesPermission):
    permission = zaakproces_usertasks


class CanSendMessages(RulesPermission):
    permission = zaakproces_send_message
