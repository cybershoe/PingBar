"""Updates package for PingrThingr.

Provides functionality to check for application updates from GitHub releases.
This package handles version comparison using semantic versioning to determine
when newer versions of the application are available.
"""

from .update_check import get_latest_release