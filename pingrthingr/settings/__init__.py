"""Settings and configuration management package.

Provides models, validation, persistence, and UI components for managing
PingrThingr application configuration and user preferences.
"""

from .settings import SettingsManager
from .selectable_menu import SelectableMenu
from .target_input import ping_target_window
from .models import ThresholdModel, IconStyle
