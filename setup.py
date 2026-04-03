"""Setup script for building PingBar macOS application.

This script uses py2app to create a standalone macOS application bundle
from the PingBar Python source code. Configures app metadata, bundle
information, and packaging options.
"""

from setuptools import setup

APP = ["main.py"]
NAME = "PingBar"
VERSION = "0.1.2"
DATA_FILES = []
OPTIONS = {
    "argv_emulation": True,
    "plist": {
        "LSUIElement": True,
        "CFBundleName": "PingBar",
        "CFBundleDisplayName": "PingBar",
        "CFBundleGetInfoString": "Made by Adam Schumacher",
        "CFBundleIdentifier": "com.genericor.PingBar",
        "CFBundleVersion": VERSION,
        "CFBundleShortVersionString": VERSION,
        "NSHumanReadableCopyright": "Copyright \u00a9 2026, Adam Schumacher, Released under the MIT License",
    },
    "packages": ["rumps"],
    "iconfile": "pingbar.icns",
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
