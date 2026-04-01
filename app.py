"""PingBar macOS menu bar application.

This module contains the main application class for PingBar, a macOS menu bar
application that monitors network connectivity by pinging specified targets.
"""

from rumps import App, clicked, alert, notification
from pinger import Pinger
from json import dump as json_dump, load as json_load

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
        
        Args:
            *args: Variable length argument list passed to parent App class.
            **kwargs: Arbitrary keyword arguments passed to parent App class.
        """
        super(PingBarApp, self).__init__(*args, **kwargs)
        self.pinger = Pinger()
        self.settings = {}

    def _load_settings(self):
        """Load application settings from settings.json file.
        
        Attempts to load settings from the settings.json file. If the file
        doesn't exist or contains invalid JSON, default settings are used.
        """
        try:
            with self.open('settings.json', 'r') as f:
                self.settings = json_load(f)
        except (IOError, ValueError):
            self.settings = {
                "paused": False,
                "airplane_mode": False,
                "targets": [
                    "8.8.8.8",
                    "1.1.1.1"
                ]
            }

    def _save_settings(self):
        """Save current application settings to settings.json file.
        
        Persists the current settings dictionary to the settings.json file
        in JSON format.
        """
        with self.open('settings.json', 'w') as f:
            json_dump(self.settings, f)       

    def set_setting(self, key, value):
        """Set a setting value and save to file.
        
        Args:
            key (str): The setting key to update.
            value: The value to set for the key.
        """
        self.settings[key] = value
        self._save_settings()

    def get_setting(self, key, default=None):
        """Get a setting value.
        
        Args:
            key (str): The setting key to retrieve.
            default: Default value to return if key doesn't exist.
            
        Returns:
            The setting value or the default value if key doesn't exist.
        """
        return self.settings.get(key, default)

    @clicked("Preferences")
    def prefs(self, _):
        """Handle preferences menu item click.
        
        Currently displays a placeholder alert. Future versions could
        open a preferences window.
        
        Args:
            _: Unused menu item parameter.
        """
        alert("jk! no preferences available!")

    @clicked("Silly button")
    def onoff(self, sender):
        """Toggle the pinger on/off state.
        
        Toggles the menu item state and starts/stops the pinger accordingly.
        
        Args:
            sender: The menu item that was clicked.
        """
        sender.state = not sender.state
        self.pinger.run(sender.state)


    @clicked("Say hi")
    def sayhi(self, _):
        """Display a test notification.
        
        Shows a sample notification to test the notification system.
        
        Args:
            _: Unused menu item parameter.
        """
        notification("Awesome title", "amazing subtitle", "hi!!1")