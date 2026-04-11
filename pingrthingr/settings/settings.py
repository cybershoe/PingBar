"""Settings persistence and management for PingrThingr application.

Provides the SettingsManager class for loading, saving, and managing
application configuration with callback support for setting changes.
"""

import logging

logger = logging.getLogger(__name__)

from json import load as json_load, dump as json_dump
from typing import Callable, Any
from .models import SettingsModel


class SettingsManager:
    """Settings management for PingrThingr application.

    Provides functionality for loading, saving, and updating application settings
    with automatic persistence and callback notification system. Settings are
    validated using Pydantic models and stored in JSON format.

    Attributes:
        _settings_file (str | None): Path to the JSON settings file.
        _settings (SettingsModel): Current application settings.
        _callbacks (dict): Registered callback functions for setting changes.
    """

    def __init__(self, settings_file: str | None = None) -> None:
        """Initialize the SettingsManager.

        Loads settings from the specified file or uses defaults if the file
        doesn't exist or contains invalid data. Initializes the callback
        system for setting change notifications.

        Args:
            settings_file (str | None): Path to the JSON settings file.
                                       If None, no file persistence is used.
        """
        self._settings_file = settings_file
        self.load()
        self._callbacks = {}

    def load(self) -> None:
        """Load settings from the JSON file specified by self._settings_file.

        If the file does not exist or contains invalid data, default settings
        will be used. Logs appropriate messages for different failure conditions.

        Raises:
            No exceptions are raised - all errors are logged and defaults used.
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
        """Save current settings to the JSON file specified by self._settings_file.

        Serializes the current settings model to JSON format and writes to disk.
        Logs errors if the file cannot be written but does not raise exceptions.

        Raises:
            No exceptions are raised - all errors are logged.
        """
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
                f"Attempted to register callback for invalid setting {setting_name}"
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
        except KeyError as e:
            if e.args[0] == setting_name:
                logger.warning(
                    f"Attempted to deregister callback for non-existent setting '{setting_name}'"
                )
            else:
                logger.warning(
                    f"Attempted to deregister non-existent callback for setting '{setting_name}'"
                )

    def get(self, setting_name: str, default: Any = None) -> Any | None:
        """Get the current value of a specific setting.

        Args:
            setting_name (str): The name of the setting to retrieve.
            default (Any): The default value to return if the setting is not found.

        Returns:
            Any | None: The current value of the specified setting, or the default
                       value if not found.

        Raises:
            AttributeError: If the setting name is not valid.
        """
        if setting_name not in SettingsModel.model_fields.keys():
            raise AttributeError(f"Attempted to get invalid setting: {setting_name}")
        return getattr(self._settings, setting_name, default)

    def set(self, name: str, value: Any) -> None:
        """Set the value of a specific setting and trigger callbacks.

        Updates the specified setting with the new value, saves the settings
        to disk, and calls any registered callbacks for that setting.

        Args:
            name (str): The name of the setting to update.
            value (Any): The new value to set for the setting.

        Raises:
            AttributeError: If the setting name is not valid.
        """
        if name not in SettingsModel.model_fields.keys():
            logger.error(f"Attempted to set invalid setting: {name}")
            raise AttributeError(f"Attempted to set invalid setting: {name}")
        setattr(self._settings, name, value)
        self.save()

        try:
            for callback in self._callbacks[name]:
                callback(value)
        except KeyError:
            logger.debug(f"No callbacks registered for setting '{name}'")
        except TypeError as e:
            logger.error(f"Error calling callback for setting '{name}': {e}")
