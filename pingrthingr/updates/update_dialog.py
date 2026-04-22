"""Dialog to notify user of available updates

Provides the update_dialog function that displays a dialog with new
version information and an option to open the release page in the browser.
"""

import logging

logger = logging.getLogger(__name__)

from rumps import Window
from webbrowser import open as open_in_browser


def update_dialog(  # pragma: no cover
    new_version: str,
    current_version: str,
    release_url: str,
    error: str,
) -> None:
    """Display an update notification dialog to the user.

    Shows a dialog with information about available updates, current version
    status, or error messages from the update check process:

    - Update available: shows both versions and offers to open the release page.
    - Up to date: confirms the current version is the latest.
    - Error: reports the error message.

    Args:
        new_version (str): Version string of the available update, or empty string
            if none.
        current_version (str): Currently installed version string.
        release_url (str): URL to the GitHub release page for the new version.
        error (str): Error message if the update check failed, or empty string on
            success.
    """

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
