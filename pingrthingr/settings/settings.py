import logging

logger = logging.getLogger(__name__)

from rumps import MenuItem, Window, alert
from socket import inet_aton
from json import load as json_load, dump as json_dump, dumps as json_dumps
from typing import List, Callable
from .models import SettingsModel


class SettingsManager():
    """Settings management for PingrThingr application.

    Provides functionality for loading, saving, and updating application settings, including callback functions for changes to particular settings.
    """
    def __init__(self, settings_file: str | None = None):
        self._settings_file = settings_file
        self.load_settings()

    def load_settings(self) -> None:
        """Load settings from the JSON file specified by self._settings_file.

        If the file does not exist or contains invalid data, defaults will be used.
        """
        if self._settings_file is None:
            logger.warning("No settings file specified, using default settings")
            return
        try:
            with open(self._settings_file, "r") as f:
                data = json_load(f)
                self._settings = SettingsModel(**data)
                logger.info(f"Settings loaded from {self._settings_file}")
        except FileNotFoundError:
            logger.info(f"Settings file {self._settings_file} not found, using default settings")
            self._settings = SettingsModel()
        except Exception as e:
            logger.error(f"Error loading settings from {self._settings_file}: {e}, using default settings")
            self._settings = SettingsModel()
        
        logger.debug(f"Current settings after loading: \n{self._settings.model_dump_json(indent=2)}")

def update_ping_targets(targets: List[str]) -> List[str] | None:
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
        logger.debug(f"In update_ping_targets(): Current targets: {targets}")
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
                f"In update_ping_targets(): User entered targets: {response.text}"
            )
            new_targets = [t.strip() for t in response.text.split(",") if t.strip()]
            try:
                for target in new_targets:
                    inet_aton(target)
            except OSError:
                alert(f"Invalid IP address: {target}")
                logger.error(
                    f"In update_ping_targets(): Invalid IP address entered: {target}"
                )
            else:
                logger.debug(
                    f"In update_ping_targets(): Valid targets entered, returning: {new_targets}"
                )
                return new_targets
        else:
            logger.info("User cancelled preferences dialog")
            return None
