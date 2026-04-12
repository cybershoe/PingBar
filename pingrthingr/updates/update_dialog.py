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
    
    Shows a dialog with information about available updates, current version status,
    or error messages from the update check process. The dialog's appearance and
    behavior changes based on the update status:
    
    - If update available: Shows versions and offers to open release page
    - If up to date: Shows current version confirmation  
    - If error occurred: Shows error message
    
    Args:
        new_version (str): Version string of available update, empty if none available
        current_version (str): Currently installed version string
        release_url (str): URL to the GitHub release page for the new version
        error (str): Error message if update check failed, empty string on success
        
    Returns:
        None
        
    Side Effects:
        - Displays a modal dialog window to the user
        - May open the default web browser to the release page if user chooses to update
        
    Note:
        This function is marked with pragma: no cover as it involves UI interaction
        that is difficult to test automatically. The dialog will block main thread
        execution  until the user responds or dismisses it.
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
