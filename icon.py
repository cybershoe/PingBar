"""Icon generation module for PingBar application.

This module provides functions to create NSImage icons for displaying
network status information in the macOS menu bar, including status text
with color-coded thresholds and SF Symbol icons.
"""

from AppKit import (
    NSImage,
    NSColor,
    NSMakeRect,
    NSSize,
    NSString,
    NSFont,
    NSForegroundColorAttributeName,
    NSFontAttributeName,
)
from Foundation import NSUserDefaults

def status_text_icon(
    latency: float | None,
    loss: float | None,
    latency_warn_threshold: float = 80.0,
    latency_alert_threshold: float = 500.0,
    latency_critical_threshold: float = 1000.0,
    loss_warn_threshold: float = 0.00,
    loss_alert_threshold: float = 0.05,
    loss_critical_threshold: float = 0.25,
):
    """Create a status text icon showing latency and loss with color-coded thresholds.
    
    This function generates a two-line NSImage icon displaying network latency
    and packet loss values. The background color changes based on configurable
    thresholds: normal (no background), warning (yellow), alert (orange), and
    critical (red).
    
    Args:
        latency (float | None): Network latency in milliseconds, or None if unavailable.
        loss (float | None): Packet loss as a decimal (0.0-1.0), or None if unavailable.
        latency_warn_threshold (float): Warning threshold for latency in ms. Defaults to 80.0.
        latency_alert_threshold (float): Alert threshold for latency in ms. Defaults to 500.0.
        latency_critical_threshold (float): Critical threshold for latency in ms. Defaults to 1000.0.
        loss_warn_threshold (float): Warning threshold for loss as decimal. Defaults to 0.00.
        loss_alert_threshold (float): Alert threshold for loss as decimal. Defaults to 0.05.
        loss_critical_threshold (float): Critical threshold for loss as decimal. Defaults to 0.25.
    
    Returns:
        NSImage: A 50x20 pixel icon with right-aligned text showing latency and loss values.
    """
    
    size = NSSize(50, 20)

    # Determine text color based on system appearance
    defaults = NSUserDefaults.standardUserDefaults()
    dark_mode = defaults.stringForKey_("AppleInterfaceStyle") == "Dark"
    if dark_mode:
        theme_color = NSColor.whiteColor()
    else:
        theme_color = NSColor.blackColor()

    image = NSImage.alloc().initWithSize_(size)

    image.lockFocus()

    # Set up font and attributes
    normalFont = NSFont.systemFontOfSize_(9)
    boldFont = NSFont.boldSystemFontOfSize_(9)

    latency_thresholds = [
        latency_warn_threshold,
        latency_alert_threshold,
        latency_critical_threshold,
    ]

    loss_thresholds = [
        loss_warn_threshold,
        loss_alert_threshold,
        loss_critical_threshold,
    ]

    for idx, (value, thresholds) in enumerate(((loss, loss_thresholds), (latency, latency_thresholds))):
      # set text color and background based on thresholds

        match value:
            case None:
                text_color = theme_color
                font = normalFont
            case v if v <= thresholds[0]:
                text_color = theme_color
                font = normalFont
            case v if v <= thresholds[1]:
                text_color = NSColor.blackColor()
                font = boldFont
                rect = NSMakeRect(0, (10*idx), size.width, 10)
                NSColor.yellowColor().drawSwatchInRect_(rect)
            case v if v <= thresholds[2]:
                text_color = NSColor.blackColor()
                font = boldFont
                rect = NSMakeRect(0, (10*idx), size.width, 10)
                NSColor.orangeColor().drawSwatchInRect_(rect)
            case _:
                text_color = NSColor.whiteColor()
                font = boldFont
                rect = NSMakeRect(0, (10*idx), size.width, 10)
                NSColor.redColor().drawSwatchInRect_(rect)
        
        attributes = {NSForegroundColorAttributeName: text_color, NSFontAttributeName: font}

        text = f'{value * (1 if idx else 100):.1f}' if value is not None else "---"
        text += " ms" if idx else " %"
        value_text = NSString.stringWithString_(text)
        value_size = value_text.sizeWithAttributes_(attributes)
        value_x = size.width - value_size.width - 2
        value_text.drawAtPoint_withAttributes_((value_x  - 4 + (4*idx), (10*idx)), attributes)

    image.unlockFocus()
    return image


def symbol_icon(symbol_name: str, accessibility_description: str) -> NSImage:
    """Create a template icon from an SF Symbol.
    
    This function creates a 20x20 pixel NSImage icon from the specified SF Symbol,
    suitable for use in macOS menu bars. The resulting image is set as a template
    image for automatic theming.
    
    Args:
        symbol_name (str): The name of the SF Symbol (e.g., 'pause.circle').
        accessibility_description (str): Accessibility description for the icon.
    
    Returns:
        NSImage: A 20x20 pixel template icon of the specified SF Symbol.
    """
    # Create SF Symbol image
    symbol_image = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
        symbol_name, accessibility_description
    )

    # Create a new 20x20 image
    size = NSSize(20, 20)
    resized_image = NSImage.alloc().initWithSize_(size)

    resized_image.lockFocus()

    # Draw the symbol image scaled to fit the 20x20 size
    symbol_image.drawInRect_(NSMakeRect(0, 0, 20, 20))

    resized_image.unlockFocus()
    resized_image.setTemplate_(True)
    return resized_image
