import logging

logger = logging.getLogger(__name__)

from rumps import MenuItem, Window, alert
from socket import inet_aton
from json import load as json_load, dump as json_dump, dumps as json_dumps
from typing import List, Callable, Any
from .models import SettingsModel


class SettingsManager:
    """Settings management for PingrThingr application.

    Provides functionality for loading, saving, and updating application settings, including callback functions for changes to particular settings.
    """

    def __init__(self, settings_file: str | None = None):
        self._settings_file = settings_file
        self.load()
        self._callbacks = {}

    def load(self) -> None:
        """Load settings from the JSON file specified by self._settings_file.

        If the file does not exist or contains invalid data, defaults will be used.
        """
        if self._settings_file is None:
            logger.warning("No settings file specified, using default settings")
            self._settings = SettingsModel()
            return
        try:
            with open(self._settings_file, "r") as f:
                data = json_load(f)
                self._settings = SettingsModel(**data)
                logger.info(f"Settings loaded from {self._settings_file}")
        except FileNotFoundError:
            logger.info(
                f"Settings file {self._settings_file} not found, using default settings"
            )
            self._settings = SettingsModel()
        except Exception as e:
            logger.error(
                f"{e.__class__.__name__} loading settings from {self._settings_file}: {e}, using default settings"
            )
            self._settings = SettingsModel()

        logger.debug(
            f"Current settings after loading: \n{self._settings.model_dump_json(indent=2)}"
        )

    def save(self) -> None:
        """Save current settings to the JSON file specified by self._settings_file."""
        if self._settings_file is None:
            logger.warning("No settings file specified, cannot save settings")
            return
        try:
            with open(self._settings_file, "w") as f:
                json_dump(self._settings.model_dump(), f, indent=2)
                logger.info(f"Settings saved to {self._settings_file}")
        except (OSError, PermissionError) as e:
            logger.error(
                f"{e.__class__.__name__} saving settings to {self._settings_file}: {e}"
            )

    def register_callback(self, setting_name: str, callback: Callable) -> None:
        """Register a callback function to be called when a specific setting changes.

        Args:
            setting_name (str): The name of the setting to watch for changes.
            callback (Callable): The function to call when the setting changes. It will be called with the new value of the setting as its argument.
        """
        if setting_name not in SettingsModel.model_fields.keys():
            logger.error(
                f"Attempted to register callback for invalid setting: {setting_name}"
            )
        self._callbacks.setdefault(setting_name, set()).add(callback)

        logger.debug(f"Registered callback for setting '{setting_name}'")

    def deregister_callback(self, setting_name: str, callback: Callable) -> None:
        """Deregister a previously registered callback function for a specific setting.

        Args:
            setting_name (str): The name of the setting the callback was registered for.
            callback (Callable): The function to deregister.
        """
        try:
            self._callbacks[setting_name].remove(callback)
            logger.debug(f"Deregistered callback for setting '{setting_name}'")
        except KeyError:
            logger.warning(
                f"Attempted to deregister callback for non-existent setting '{setting_name}'"
            )
        except ValueError:
            logger.warning(
                f"Attempted to deregister non-existent callback for setting '{setting_name}'"
            )

    def get(self, setting_name: str, default: Any = None) -> Any | None:
        """Get the current value of a specific setting.

        Args:
            setting_name (str): The name of the setting to retrieve.
            default: The default value to return if the setting is not found.

        Returns:
            The current value of the specified setting, or the default value if not found.
        """
        if setting_name not in SettingsModel.model_fields.keys():
            raise ValueError(f"Attempted to get invalid setting: {setting_name}")
        return getattr(self._settings, setting_name, default)

    def set(self, name: str, value: Any) -> None:
        if name not in SettingsModel.model_fields.keys():
            logger.error(f"Attempted to set invalid setting: {name}")
            raise ValueError(f"Attempted to set invalid setting: {name}")
        setattr(self._settings, name, value)
        self.save()

        try:
            for callback in self._callbacks[name]:
                callback(value)
        except KeyError:
            logger.debug(f"No callbacks registered for setting '{name}'")
        except TypeError as e:
            logger.error(f"Error calling callback for setting '{name}': {e}")


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
