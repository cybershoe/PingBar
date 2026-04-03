"""PingBar macOS menu bar application.

This module contains the main application class for PingBar, a macOS menu bar
application that monitors network connectivity by pinging specified targets.
"""
import logging
logger = logging.getLogger(__name__)

from rumps import App, clicked, MenuItem, timer
from json import dump as json_dump, load as json_load
from pinger import Pinger
from icon import status_text_icon, status_dot_icon, symbol_icon
from preferences import get_preferences



class PingBarApp(App):
    """Main application class for PingBar menu bar app.

    Extends the rumps.App class to provide a macOS menu bar application
    for network connectivity monitoring. Manages settings persistence
    and provides user interface controls for the pinger functionality.

    Attributes:
        pinger (Pinger): The network pinger instance.
        settings (dict): Application settings dictionary.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the PingBar application.
        
        Sets up the menu bar application with default settings, creates the
        status menu items, initializes the pinger, and loads any saved
        configuration from the settings file.

        Args:
            *args: Variable length argument list passed to parent App class.
            **kwargs: Arbitrary keyword arguments passed to parent App class.
        """
        super(PingBarApp, self).__init__(*args, **kwargs)
        self.settings = {}
        self._load_settings()
        self.latency = None
        self.loss = None
        self.title = None
        self._icon_nsimage = symbol_icon("pause.circle" if self.get_setting("paused", False) else "waveform.path.ecg", "PingBar")
        self.statistics_menu = MenuItem("waiting...")
        self.pause_menu = MenuItem("Pause")
        self.pause_menu.state = self.get_setting("paused", False)
        self.menu = [self.statistics_menu, self.pause_menu]
        self._changed = False

        self.pinger = Pinger(
            targets=self.settings.get("targets", []),
            start_running=not self.settings.get("paused", False),
            cb=self.update_statistics,
        )
        logger.info(f"Initialized PingBar")

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
        if key == "paused":
            self.pinger.run(not value)
            self.pause_menu.state = value
            self.latency = None
            self.loss = None
            self._changed = True

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
    

    def update_statistics(self, latency: float = None, loss: float = None):
        """Update the statistics display with new network measurements.

        Called by the pinger when new latency and packet loss measurements
        are available. Updates internal state and triggers a menu refresh.

        Args:
            latency (float, optional): The average latency in milliseconds. Defaults to None.
            loss (float, optional): The packet loss as a decimal (0.0-1.0). Defaults to None.
        """
        logger.debug(f"In update_statistics(): Updating statistics: loss={self.loss}, latency={self.latency}")

        if latency is not None:
            self.latency = latency
        if loss is not None:
            self.loss = loss

        self._changed = True


    
    @timer(1)
    def refresh_menu(self, _):
        """Refresh the statistics menu item text every second."""

        if self._changed:
            self._changed = False
            if self.settings.get("paused"):
                logger.debug(f"In refresh_menu(): Application is paused, showing paused status")
                self.statistics_menu.title = "Paused"
                self._icon_nsimage = symbol_icon("pause.circle", "Paused")
            else:
                logger.debug(f"In refresh_menu(): Application is running, showing latency and loss")
                loss_str = f"{(self.loss*100):.2f}%" if self.loss is not None else "N/A"
                latency_str = f"{(self.latency):.2f} ms" if self.latency is not None else "N/A"
                self.statistics_menu.title = f"Loss: {loss_str}, Latency: {latency_str}"
                self._icon_nsimage = status_dot_icon(self.latency, self.loss)
            self._nsapp.setStatusBarIcon()

    @clicked("Ping targets")
    def prefs(self, _):
        """Handle preferences menu item click.

        Currently displays a placeholder alert. Future versions could
        open a preferences window.

        Args:
            _: Unused menu item parameter.
        """
        new_targets = get_preferences(self.get_setting("targets", []))
        if new_targets is not None:
            logger.debug(f"Updating targets from get_preferences: {new_targets}")
            self.set_setting("targets", new_targets)
        else:
            logger.debug(f"get_preferences returned None, no changes to targets")

    @clicked("Pause")
    def onoff(self, sender):
        """Toggle the pinger on/off state.

        Toggles the menu item state and starts/stops the pinger accordingly.

        Args:
            sender: The menu item that was clicked.
        """
        logger.debug(f"Toggling pause state from {self.get_setting('paused', None)} to {not self.get_setting('paused', None)}")
        self.set_setting("paused", not self.get_setting("paused", False))
        sender.state = self.get_setting("paused", False)
        self.refresh_menu(self)

