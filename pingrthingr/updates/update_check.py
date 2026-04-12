"""Update checking module for PingrThingr application.

This module provides functionality to check for new releases of PingrThingr
by querying the GitHub API and comparing version numbers using semantic versioning.
"""

import logging

logger = logging.getLogger(__name__)

REPO = "cybershoe/PingrThingr"

from httpx import AsyncClient, HTTPStatusError
from typing import Tuple, Callable
import asyncio
from threading import Thread

from semver import Version


def run_update_check(
    current_version_name: str, callback: Callable, quiet: bool = False
) -> None:
    """Run the update check in a separate thread to avoid blocking the UI."""

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


    """

    response = None
    url = f"https://api.github.com/repos/{REPO}/releases/latest"
    logger.debug(f"Fetching latest release from {url}")
    try:
        async with AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
    except HTTPStatusError as e:
        logger.error(f"HTTP error occurred fetching latest release: {e}")
        if not quiet:
            callback("", "", f"HTTP error occurred: {e}")
        return

    if response is not None:
        if response.status_code == 200:
            data = response.json()
            latest_version_tag = data.get("tag_name")
            latest_version_name = latest_version_tag.removesuffix("-release")
            logger.debug(f"Latest release version: {latest_version_tag}")
            try:
                latest_version = Version.parse(latest_version_name.removeprefix("v"))
                current_version = Version.parse(current_version_name.removeprefix("v"))
                if latest_version > current_version:
                    logger.info(
                        f"New version available: {latest_version} (current: {current_version})"
                    )
                    callback(latest_version_name, data.get("html_url", ""), "")
                    return
                else:
                    logger.debug("No new version available.")
                    if not quiet:
                        callback("", "", f"{current_version} is the latest version.")
                    return
            except TypeError as e:
                logger.error(
                    f"Error parsing version from tag '{latest_version_tag}': {e}"
                )
                if not quiet:
                    callback("", "", f"Error parsing version: {e}")
                return

        else:
            logger.debug(f"Failed to fetch latest release: {response.status_code}")

    if not quiet:
        callback("", "", "Unknown error")
