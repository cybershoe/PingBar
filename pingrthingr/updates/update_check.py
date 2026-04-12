"""Update checking module for PingrThingr application.

This module provides functionality to check for new releases of PingrThingr
by querying the GitHub API and comparing version numbers using semantic versioning.
"""

import logging

logger = logging.getLogger(__name__)

REPO = "cybershoe/PingrThingr"

from httpx import AsyncClient, HTTPError
from typing import Tuple, Callable
import asyncio
from threading import Thread

from semver import Version


def run_update_check(
    current_version_name: str, callback: Callable, quiet: bool = False
) -> None:
    """Run the update check in a separate thread to avoid blocking the UI.

    Initiates an asynchronous update check that queries GitHub for the latest
    release and compares it with the current version. The check runs in a
    separate thread to prevent blocking the main UI thread.

    Args:
        current_version_name (str): The current version string to compare against
        callback (Callable): Function to call with results (new_version, url, error)
        quiet (bool, optional): Passed to callback to indicate whether to suppress dialogs
        for "up to date" status. Defaults to False.

    Note:
        The callback will be called with three string parameters:
        - new_version: Version string if update available, empty if not
        - url: Release URL if update available, empty otherwise
        - error: Error message if check failed, empty on success
    """

    thread = Thread(
        target=lambda: asyncio.run(
            _check_for_updates(current_version_name, callback, quiet)
        )
    )
    thread.start()


async def _check_for_updates(
    current_version_name: str, callback: Callable, quiet: bool = False
) -> None:
    """Check for the latest release of PingrThingr on GitHub.

    Queries the GitHub API to fetch information about the latest release,
    compares it with the current version using semantic versioning, and
    determines if an update is available.

    The function handles version tag parsing by removing common prefixes/suffixes
    like 'v' and '-release' to ensure proper semantic version comparison.

    Args:
        current_version_name (str): Current version string (e.g., "1.2.3" or "v1.2.3")
        callback (Callable): Function to call with results (new_version, url, error, quiet)
        quiet (bool, optional): Passed to callback to indicate whether to suppress dialogs
        for "up to date" status. Defaults to False.

    Note:
        This is an internal async function called by run_update_check().
        The callback signature is: callback(new_version: str, url: str, error: str, quiet: bool)
    """

    response = None
    url = f"https://api.github.com/repos/{REPO}/releases/latest"
    logger.debug(f"Fetching latest release from {url}")
    try:
        async with AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
    except HTTPError as e:
        logger.error(f"HTTP error occurred fetching latest release: {e}")
        callback("", "", f"HTTP error occurred: {e}", quiet)
        return

    if response is not None:  # pragma: no branch
        if response.status_code == 200:
            data = response.json()
            latest_version_tag = data.get("tag_name")
            latest_version_name = latest_version_tag.removesuffix("-release")
            logger.debug(f"Latest release version tag: {latest_version_tag}")
            logger.debug(f"Latest release version name: {latest_version_name}")
            try:
                latest_version = Version.parse(latest_version_name.removeprefix("v"))
                current_version = Version.parse(current_version_name.removeprefix("v"))
                if latest_version > current_version:
                    logger.info(
                        f"New version available: {latest_version} (current: {current_version})"
                    )
                    callback(latest_version_name, data.get("html_url", ""), "", quiet)
                    return
                else:
                    logger.debug("No new version available.")
                    callback("", "", f"{current_version_name} is the latest version.", quiet)
                    return
            except ValueError as e:
                logger.error(
                    f"Error parsing version from tag '{latest_version_tag}': {e}"
                )
                callback("", "", f"Error parsing version: {e}", quiet)
                return

        else:
            logger.debug(f"Failed to fetch latest release: {response.status_code}")

    callback("", "", "Unknown error", quiet)
