from zac.api.permissions import DefinitionBasePermission
from zac.core.permissions import zaakproces_send_message, zaakproces_usertasks


class CanPerformTasks(DefinitionBasePermission):
    permission = zaakproces_usertasks


class CanSendMessages(DefinitionBasePermission):
    permission = zaakproces_send_message
