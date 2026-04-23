"""PingrThingr - macOS menu bar network connectivity monitor.

This package provides a macOS menu bar application that monitors network
connectivity by pinging specified targets and displays status icons.
"""

from .app import PingrThingrApp
from .version import __VERSION__
from .about import show_about_window
from .network import NetworkStatus
