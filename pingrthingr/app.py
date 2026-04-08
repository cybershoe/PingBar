"""PingrThingr macOS menu bar application.

This module contains the main application class for PingrThingr, a macOS menu bar
application that monitors network connectivity by pinging specified targets.
"""

import logging

logger = logging.getLogger(__name__)

from rumps import App, clicked, MenuItem, timer, application_support
from os.path import join as path_join
from json import dump as json_dump, load as json_load
from .pinger import Pinger
from .icons import status_text_icon, status_dot_icon, symbol_icon
from .settings import SelectableMenu, update_ping_targets, SettingsManager
from objc import selector as objc_selector
from Foundation import NSOperationQueue, NSBlockOperation


class PingrThingrApp(App):
    """Main application class for PingrThingr menu bar app.

    Extends the rumps.App class to provide a macOS menu bar application
    for network connectivity monitoring. Manages settings persistence
    and provides user interface controls for the pinger functionality.

    Attributes:
        pinger (Pinger): The network pinger instance.
        settings (dict): Application settings dictionary.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the PingrThingr application.

        Sets up the menu bar application with default settings, creates the
        status menu items, initializes the pinger, and loads any saved
        configuration from the settings file.

        Args:
            *args: Variable length argument list passed to parent App class.
            **kwargs: Arbitrary keyword arguments passed to parent App class.
        """
        super(PingrThingrApp, self).__init__(*args, **kwargs)
        self._settings_path = path_join(application_support(self.name), "settings.json")
        logger.debug(f"Settings file path: {self._settings_path}")
        self._settings = SettingsManager(self._settings_path)
        # self._load_settings()
        self.latency = None
        self.loss = None
        self.title = None
        self._icon_nsimage = symbol_icon(
            (
                "pause.circle"
                if self._settings.get("paused", False)
                else "waveform.path.ecg"
            ),
            "PingrThingr",
        )
        self.statistics_menu = MenuItem("waiting...")
        self.pause_menu = MenuItem("Pause")
        self.display_menu = SelectableMenu(
            "Display Mode",
            options=["Dot", "Text"],
            selected=self._settings.get("display_mode", "Dot"),
            cb=self.set_display_mode,
        )
        self.pause_menu.state = self._settings.get("paused", False)
        self.menu = [self.statistics_menu, self.pause_menu, self.display_menu]
        # self._changed = False
        self._last_state = None

        self.pinger = Pinger(
            targets=self._settings.get("targets", []),  # type: ignore
            start_running=not self._settings.get("paused", False),
            cb=self.update_statistics,
        )

        self._settings.register_callback("paused", self.pause_cb)
        self._settings.register_callback("targets", self.ping_targets_cb)

        logger.info(f"Initialized PingrThingr")

    def _load_settings(self):
        """Load application settings from settings.json file.

        Attempts to load settings from the settings.json file. If the file
        doesn't exist or contains invalid JSON, default settings are used.
        """
        try:
            with self.open("settings.json", "r") as f:
                self.settings = json_load(f)
                logger.info(f"Settings loaded from settings.json")
        except (IOError, ValueError):
            self.settings = {
                "paused": False,
                "targets": ["8.8.8.8", "1.1.1.1", "8.8.4.4", "1.0.0.1"],
                "display_mode": "Dot",
            }
            logger.warning(f"Failed to load settings.json, using default settings")

        logger.debug(f"In _load_settings(): Loaded settings: {self.settings}")

    def _save_settings(self):
        """Save current application settings to settings.json file.

        Persists the current settings dictionary to the settings.json file
        in JSON format.
        """
        with self.open("settings.json", "w") as f:
            json_dump(self.settings, f)
        logger.info(f"In _save_settings(): Settings saved to settings.json")

    def set_setting(self, key, value):
        """Set a setting value and save to file.

        Args:
            key (str): The setting key to update.
            value: The value to set for the key.
        """
        self.settings[key] = value
        logger.debug(f"In set_setting(): Setting updated: {key} = {value}")
        if key == "targets":
            self.pinger.targets = value
        # if key == "paused":
        #     self.pinger.run(not value)
        #     self.pause_menu.state = value
        #     self.latency = None
        #     self.loss = None
        #     self._changed = True

        self._save_settings()

    def get_setting(self, key, default=None):
        """Get a setting value.

        Args:
            key (str): The setting key to retrieve.
            default: Default value to return if key doesn't exist.

        Returns:
            The setting value or the default value if key doesn't exist.
        """
        logger.debug(f"In get_setting(): Retrieving setting: {key} (default={default})")
        return self.settings.get(key, default)

    def pause_cb(self, paused: bool):
        """Pause or resume the pinger.

        Args:
            paused (bool): True to pause the pinger, False to resume.
        """
        self.pinger.run(not paused)
        self.pause_menu.state = paused
        self.latency = None
        self.loss = None
        self.refresh_status_(use_saved=True)

    def ping_targets_cb(self, targets: list[str]):
        """Set the list of ping target IP addresses.

        Args:
            targets (list[str]): List of IP addresses to ping.
        """
        self.pinger.targets = targets

    def set_display_mode(self, mode: str) -> None:
        """Set the display mode for the status icon.

        Updates the display mode setting and triggers a visual refresh
        of the menu bar icon.

        Args:
            mode (str): The display mode to set.
        """
        logger.debug(f"In set_display_mode(): Setting display_mode to {mode}")
        self.set_setting("display_mode", mode)
        self._changed = True
        self.refresh_status_(use_saved=True)

    def update_statistics(self, latency: float | None = None, loss: float | None = None) -> None:
        """Update the statistics display with new network measurements.

        Called by the pinger when new latency and packet loss measurements
        are available. Updates internal state and triggers a display refresh.

        Args:
            latency (float, optional): The average latency in milliseconds. Defaults to None.
            loss (float, optional): The packet loss as a decimal (0.0-1.0). Defaults to None.
        """
        
        logger.debug(
            f"In update_statistics(): Updating statistics: loss={loss}, latency={latency}"
        )

        operation = NSBlockOperation.blockOperationWithBlock_(lambda: self.refresh_status_(latency, loss))
        NSOperationQueue.mainQueue().addOperation_(operation)

    @objc_selector
    def refresh_status_(self, latency: float | None = None, loss: float | None = None, use_saved: bool = False):
        """Refresh the status display and menu item text every second."""
        print(f"Refreshing status: latency={latency}, loss={loss}, use_saved={use_saved}")

        if use_saved:
            latency = self.latency
            loss = self.loss
        else:
            self.latency = latency
            self.loss = loss
        
        if self._settings.get("paused"):
            logger.debug(
                f"In refresh_status(): Application is paused, showing paused status"
            )
            self.statistics_menu.title = "Paused"
            self._icon_nsimage = symbol_icon("pause.circle", "Paused")
            self._nsapp.setStatusBarIcon()
        else:
            logger.debug(
                f"In refresh_status(): Application is running, showing latency and loss"
            )
            loss_str = f"{(loss*100):.2f}%" if loss is not None else "---"
            latency_str = (
                f"{(latency):.2f} ms" if latency is not None else "---"
            )
            self.statistics_menu.title = f"Loss: {loss_str}, Latency: {latency_str}"
            display = self._settings.get("display_mode", "Dot")
            logger.debug(f"In refresh_status(): Current display_mode: {display}")

            match display:
                case "Dot":
                    icon, new_state = status_dot_icon(
                        latency, loss, self._last_state
                    )

                case "Text":
                    icon, new_state = status_text_icon(
                        latency, loss, self._last_state
                    )
                case _:
                    raise ValueError(
                        f"Invalid display_mode setting: {self.settings.get('display_mode')}"
                    )

            logger.debug(
                f"In refresh_status(): Last state: {self._last_state}, new state: {new_state}"
            )
            self._last_state = new_state

            if icon is not None:
                logger.debug(
                    f"In refresh_status(): Updating icon for new state: {new_state}"
                )
                self._icon_nsimage = icon
                self._nsapp.setStatusBarIcon()

    @clicked("Ping targets")
    def ping_targets(self, _):
        """Handle ping targets menu item click.

        Displays the preferences dialog for configuring ping target IP addresses
        and updates settings if the user saves changes.

        Args:
            _: Unused menu item parameter.
        """
        new_targets = update_ping_targets(self._settings.get("targets", []))  # type: ignore
        if new_targets is not None:
            logger.debug(f"Updating targets from update_ping_targets(): {new_targets}")
            self._settings.set("targets", new_targets)
        else:
            logger.debug(f"update_ping_targets() returned None, no changes to targets")

    @clicked("Pause")
    def pause_toggle(self, sender):
        """Toggle the pinger on/off state.

        Toggles the menu item state and starts/stops the pinger accordingly.

        Args:
            sender: The menu item that was clicked.
        """
        logger.debug(
            f"Toggling pause state from {sender.state} to {not sender.state}"
        )

        self._settings.set("paused", not sender.state)
        # self.set_setting("paused", not self.get_setting("paused", False))
        # sender.state = self.get_setting("paused", False)
        # self.refresh_status_(use_saved=True)
