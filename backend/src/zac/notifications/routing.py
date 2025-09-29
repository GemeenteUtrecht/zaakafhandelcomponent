import logging
from typing import Any, Dict, Optional, Protocol

from .handlers.documenten import InformatieObjectenHandler
from .handlers.informatieobjecttypen import InformatieObjecttypenHandler
from .handlers.objecten import ObjectenHandler
from .handlers.zaaktypen import ZaaktypenHandler
from .handlers.zaken import ZakenHandler

logger = logging.getLogger(__name__)

Notification = Dict[str, Any]


class HandlesMessages(Protocol):
    def handle(self, message: Notification) -> None:
        ...


class RoutingHandler:
    """Routes a single notification to the handler for its kanaal."""

    def __init__(
        self,
        config: Dict[str, HandlesMessages],
        default: Optional[HandlesMessages] = None,
    ) -> None:
        self.config = config
        self.default = default

    def handle(self, message: Notification) -> None:
        handler = self.config.get(message.get("kanaal"))
        if handler is not None:
            handler.handle(message)
        elif self.default:
            self.default.handle(message)
        else:
            logger.debug("No routing handler for kanaal=%s", message.get("kanaal"))


handler = RoutingHandler(
    {
        "zaaktypen": ZaaktypenHandler(),
        "informatieobjecttypen": InformatieObjecttypenHandler(),
        "zaken": ZakenHandler(),
        "objecten": ObjectenHandler(),
        "documenten": InformatieObjectenHandler(),
    }
)
