"""Setup script for building PingrThingr macOS application.

This script uses py2app to create a standalone macOS application bundle
from the PingrThingr Python source code. Configures app metadata, bundle
information, and packaging options.
"""

from setuptools import setup

APP = ["main.py"]
NAME = "PingrThingr"
VERSION = "0.2.0"
DATA_FILES = []
OPTIONS = {
    "argv_emulation": True,
    "plist": {
        "LSUIElement": True,
        "CFBundleName": "PingrThingr",
        "CFBundleDisplayName": "PingrThingr",
        "CFBundleGetInfoString": "Made by Adam Schumacher",
        "CFBundleIdentifier": "com.genericor.PingrThingr",
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
