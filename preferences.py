"""Preferences management module for PingBar application.

This module provides functionality to display and manage user preferences,
particularly for configuring ping target IP addresses through a GUI dialog.
"""
import logging
logger = logging.getLogger(__name__)

from rumps import Window, alert
from typing import List
from socket import inet_aton

def get_preferences(targets: List[str]) -> List[str]:
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
        logger.debug(f"In get_preferences(): Current targets: {targets}")
        response = Window(
            title="Ping Targets",
            message="Enter target IP addresses (comma-separated):",
            default_text=",".join(targets),
            dimensions=(300, 24),
            cancel="Cancel",
            ok="Save",
        ).run()

        if response.clicked == 1:
            logger.debug(f"In get_preferences(): User entered targets: {response.text}")
            new_targets = [t.strip() for t in response.text.split(",") if t.strip()]
            try:
                for target in new_targets:
                    inet_aton(target)
            except OSError:
                alert(f"Invalid IP address: {target}")
                logger.error(f"In get_preferences(): Invalid IP address entered: {target}")
            else:
                logger.debug(f"In get_preferences(): Valid targets entered, returning: {new_targets}")
                return new_targets
        else:
            logger.info("User cancelled preferences dialog")
            return None
