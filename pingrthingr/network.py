import logging

logger = logging.getLogger(__name__)

from SystemConfiguration import (
    SCDynamicStoreCreate,  # type: ignore[import]
    SCDynamicStoreCopyValue,  # type: ignore[import]
)

class NetworkStatus:
    def __init__(self):
        self._store = SCDynamicStoreCreate(None, "PingrThingr", None, None)
        
    def online(self) -> bool:
        route = SCDynamicStoreCopyValue(self._store, "State:/Network/Global/IPv4")
        return route is not None
