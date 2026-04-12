"""Setup script for building PingrThingr macOS application.

This script uses py2app to create a standalone macOS application bundle
from the PingrThingr Python source code. Configures app metadata, bundle
information, and packaging options.
"""

from setuptools import setup
import subprocess
from os import getenv


# 1. Dynamically get the current git branch name
def get_branch_name():
    """Get the current git branch name for build versioning.
    
    Retrieves the current git branch name and returns it as a suffix
    for the application name. Returns empty string for the main branch.
    
    Returns:
        str: Branch name prefixed with '-' or empty string for main branch,
             or if BUILD_APPEND_BRANCH is not set to "true".
             Returns "unknown" if git command fails.
    """
    if getenv("BUILD_APPEND_BRANCH", "true").lower() == "true":
        try:
            branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True
            ).strip()
            if branch == "main" or branch.startswith("release/"):
                return ""
            return f"-{branch}"
        except subprocess.CalledProcessError:
            return "unknown"
    return ""

exec(open("pingrthingr/version.py").read())
APP = ["main.py"]
NAME = f"PingrThingr{get_branch_name().replace('/', '-')}"
VERSION = __VERSION__   # type: ignore
DATA_FILES = []
OPTIONS = {
    "argv_emulation": True,
    "plist": {
        "LSUIElement": True,
        "CFBundleName": NAME,
        "CFBundleDisplayName": NAME,
        "CFBundleGetInfoString": "Made by Adam Schumacher",
        "CFBundleIdentifier": f"com.genericor.{NAME.lower().replace(' ', '')}",
        "CFBundleVersion": VERSION,
        "CFBundleShortVersionString": VERSION,
        "NSHumanReadableCopyright": "Copyright \u00a9 2026, Adam Schumacher, Released under the MIT License",
    },
    "packages": ["rumps"],
    "iconfile": "PingrThingr.icns",
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
