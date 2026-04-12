"""Dialog to notify user of available updates

Provides the update_dialog function that displays a dialog with new
version information and an option to open the release page in the browser.
"""

import logging

logger = logging.getLogger(__name__)

from rumps import Window, alert
from webbrowser import open as open_in_browser



def update_dialog(new_version: str = "v0.5.0", release_url: str = "https://github.com/cybershoe/PingrThingr/releases/latest", error: str = "") -> None:
    response = Window(
        title="Update Available",
        message = (
            f"A new version of PingrThingr is available: {new_version}\n\n"
            "Would you like to open the release page in your browser?"
        ) if not error else (
            f"Error checking for updates: {error}\n\n"
            "Please try again later."
        ),
        dimensions=(400, 100),
        cancel="Cancel",
        ok="Open" if not error else None,
    ).run()

    if response.clicked == 1 and not error:
        open_in_browser(release_url)