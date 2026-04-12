"""Dialog to notify user of available updates

Provides the update_dialog function that displays a dialog with new
version information and an option to open the release page in the browser.
"""

import logging

logger = logging.getLogger(__name__)

from rumps import Window, alert
from webbrowser import open as open_in_browser


def update_dialog(
    new_version: str = "v0.5.0",
    current_version: str = "v0.4.0",
    release_url: str = "https://github.com/cybershoe/PingrThingr/releases/latest",
    error: str = "",
) -> None:  # pragma no cover

    if not error and new_version:
        message = (
            f"New version: {new_version}\n\n"
            f"Your current version: {current_version}\n\n"
            "Would you like to open the release page in your browser?"
        )
    elif new_version == "":
        message = f"{current_version} is the latest version."
    else:
        message = f"Error checking for updates: {error}\n\nPlease try again later."
    response = Window(
        title=(
            "A new version of PingrThingr is available"
            if new_version
            else "PingrThingr is up to date"
        ),
        message=message,
        dimensions=(0, 0),
        cancel="Not now" if new_version else None,
        ok="Get update" if new_version else None,
    ).run()

    if response.clicked == 1 and not error:
        open_in_browser(release_url)
