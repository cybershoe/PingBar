"""Update checking module for PingrThingr application.

This module provides functionality to check for new releases of PingrThingr
by querying the GitHub API and comparing version numbers using semantic versioning.
"""

import logging

logger = logging.getLogger(__name__)

REPO = "cybershoe/PingrThingr"

from httpx import AsyncClient, HTTPStatusError
from pingrthingr import __VERSION__
from typing import Tuple
from semver import Version


async def get_latest_release() -> Tuple[str, str, str]:
    """Check for the latest release of PingrThingr on GitHub.
    
    Queries the GitHub API to fetch information about the latest release,
    compares it with the current version using semantic versioning, and
    determines if an update is available.
    
    The function handles version tag parsing by removing common prefixes/suffixes
    like 'v' and '-release' to ensure proper semantic version comparison.
    
    Returns:
        Tuple[bool, str]: A tuple containing:
            - str: The new version number if an update is available, empty string otherwise
            - str: URL to the release page if update available, empty string otherwise
            - str: Error message if an error occurs, empty string otherwise

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
        return "", "", f"HTTP error occurred: {e}"

    if response is not None:
        if response.status_code == 200:
            data = response.json()
            latest_version_tag = data.get("tag_name")
            latest_version_name = latest_version_tag.removesuffix("-release")
            logger.debug(f"Latest release version: {latest_version_tag}")
            try:
                latest_version = Version.parse(
                    latest_version_name.removeprefix("v")
                )
                current_version = Version.parse(__VERSION__.removeprefix("v"))
                if latest_version > current_version:
                    logger.info(
                        f"New version available: {latest_version} (current: {current_version})"
                    )
                    return str(latest_version), data.get("html_url", ""), ""
            except TypeError as e:
                logger.error(
                    f"Error parsing version from tag '{latest_version_tag}': {e}"
                )
                return "", "", f"Error parsing version: {e}"

        else:
            logger.debug(f"Failed to fetch latest release: {response.status_code}")

    return "", "", "Unknown error"
