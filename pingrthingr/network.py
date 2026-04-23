"""
This module provides functionality to check the network status on macOS using the 
SystemConfiguration framework. It defines a NetworkStatus class that can be used to 
determine if the system is currently online by checking the presence of a default 
route in the network configuration.
"""

import logging

logger = logging.getLogger(__name__)

from SystemConfiguration import (
    SCDynamicStoreCreate,  # type: ignore[import]
    SCDynamicStoreCopyValue,  # type: ignore[import]
)


class NetworkStatus:
    def __init__(self):
        self._store = SCDynamicStoreCreate(None, "PingrThingr", None, None)

    def online(self) -> bool:  # pragma: no cover
        route = SCDynamicStoreCopyValue(self._store, "State:/Network/Global/IPv4")
        return route is not None
