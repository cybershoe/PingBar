"""Setup script for building PingrThingr macOS application.

This script uses py2app to create a standalone macOS application bundle
from the PingrThingr Python source code. Configures app metadata, bundle
information, and packaging options.
"""

from setuptools import setup
import subprocess

# 1. Dynamically get the current git branch name
def get_branch_name():
    try:
        branch = subprocess.check_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'], 
            text=True
        ).strip()
        if branch == "main":
            return ""
        return f"-{branch}"
    except subprocess.CalledProcessError:
        return "unknown"

APP = ["main.py"]
NAME = f"PingrThingr{get_branch_name()}"
VERSION = "0.2.0"
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
