"""Icon generation package for PingrThingr application.

Provides functions for creating NSImage and NSView icons that display
network status information with color-coded thresholds.
"""

from .icon import status_text_icon, generate_status_icon
from .symbol import symbol_icon
from .util import combine_template_and_color_images
