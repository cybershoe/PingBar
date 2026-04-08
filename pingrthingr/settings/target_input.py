import logging

logger = logging.getLogger(__name__)

from rumps import Window, alert
from socket import inet_aton
from json import load as json_load, dump as json_dump, dumps as json_dumps
from typing import List

def ping_target_window(targets: List[str]) -> List[str] | None:
    """Display preferences dialog for configuring ping targets.

    Shows a modal dialog window allowing the user to enter or modify
    the list of IP addresses to monitor. Validates all entered IP addresses
    and displays error messages for invalid entries.

    Args:
        targets (List[str]): Current list of target IP addresses.

    Returns:
        List[str] | None: Updated list of target IP addresses if user clicked Save,
                         or None if user clicked Cancel or closed the dialog.
    """
    while True:
        logger.debug(f"In ping_target_window(): Current targets: {targets}")
        response = Window(
            title="Ping Targets",
            message="Enter target IP addresses (comma-separated):",
            default_text=",".join(targets),
            dimensions=(300, 24),
            cancel="Cancel",
            ok="Save",
        ).run()

        if response.clicked == 1:
            logger.debug(
                f"In ping_target_window(): User entered targets: {response.text}"
            )
            new_targets = [t.strip() for t in response.text.split(",") if t.strip()]
            try:
                for target in new_targets:
                    inet_aton(target)
            except OSError:
                alert(f"Invalid IP address: {target}")
                logger.error(
                    f"In ping_target_window(): Invalid IP address entered: {target}"
                )
            else:
                logger.debug(
                    f"In ping_target_window(): Valid targets entered, returning: {new_targets}"
                )
                return new_targets
        else:
            logger.info("User cancelled preferences dialog")
            return None
