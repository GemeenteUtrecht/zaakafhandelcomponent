from typing import Dict, Optional

from ..data import Task


def noop(task) -> None:
    return None


REGISTRY: Dict[str, callable] = {
    "": noop,
    "zac:configureAdviceRequest": noop,
    "zac:configureApprovalRequest": noop,
    # below are not MVP I think, maybe even deprecated alltogether
    "zac:documentSelectie": noop,
    "zac:gebruikerSelectie": noop,
}


class Context:
    """
    Base class for user-task contexts.

    The user task context subclass is determined by the form_key.
    """

    pass


def get_context(task: Task) -> Optional[Context]:
    """
    Retrieve the task-specific context for a given user task.

    Consult the registry mapping form keys to specific context-determination functions.
    If no callback exists for a given form key, ``None`` is returned.

    Third party or non-core apps can add form keys to the registry by importing the
    ``REGISTRY`` constant and registering their form key with the appropriote callback
    callable.
    """
    callback: Optional[callable] = REGISTRY.get(task.form_key)
    if callback is None:
        return None
    return callback(task)
