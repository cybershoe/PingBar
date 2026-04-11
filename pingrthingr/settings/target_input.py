"""User interface for configuring ping target IP addresses.

Provides the ping_target_window function that displays a dialog for
user input and validation of target IP addresses for network monitoring.
"""

import logging

logger = logging.getLogger(__name__)

from rumps import Window, alert
from socket import inet_aton
from json import load as json_load, dump as json_dump, dumps as json_dumps
from typing import List


def ping_target_window(targets: List[str]) -> List[str] | None:  # pragma: no cover
    """Display preferences dialog for configuring ping targets.

    Shows a modal dialog window allowing the user to enter or modify
    the list of IP addresses to monitor. Validates all entered IP addresses
    and displays error messages for invalid entries. If validation fails,
    the dialog will be closed and None returned.

    Args:
        targets (List[str]): Current list of target IP addresses to display
                           as default values in the dialog.

    Returns:
        List[str] | None: Updated list of valid target IP addresses if user 
                         clicked Save and all entries are valid, or None if user 
                         clicked Cancel, closed the dialog, or entered invalid data.
    """
    while True:  # pragma: no cover. not feasible to test headless
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

            for target in new_targets:
                try:
                    inet_aton(target)
                except OSError:
                    alert(f"Invalid IP address: {target}")
                    logger.error(
                        f"In ping_target_window(): Invalid IP address entered: {target}"
                    )
                    return None
            logger.debug(
                f"In ping_target_window(): Valid targets entered, returning: {new_targets}"
            )
            return new_targets

        else:
            logger.info("User cancelled preferences dialog")
            return None
