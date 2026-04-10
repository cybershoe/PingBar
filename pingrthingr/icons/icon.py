"""Icon generation module for PingrThingr application.

This module provides functions to create NSImage icons for displaying
network status information in the macOS menu bar, including status text
with color-coded thresholds and SF Symbol icons.
"""

from AppKit import (
    NSImage,  # type: ignore[import]
    NSColor,  # type: ignore[import]
    NSMakeRect,  # type: ignore[import]
    NSSize,  # type: ignore[import]
    NSString,  # type: ignore[import]
    NSFont,  # type: ignore[import]
    NSForegroundColorAttributeName,  # type: ignore[import]
    NSFontAttributeName,  # type: ignore[import]
    NSImageSymbolConfiguration,  # type: ignore[import]
)
from Foundation import NSUserDefaults  # type: ignore[import]
from typing import Tuple, Literal


class StatusIcon:
    def __init__(
        self,
        style: Literal["dot", "text"] = "dot",
        latency: float | None = None,
        loss: float | None = None,
    ):
        self.style = style
        self.last_state = None
        self.latency = latency
        self.loss = loss


def status_dot_icon(
    latency: float | None,
    loss: float | None,
    last_state: str | None = None,
    latency_warn_threshold: float = 80.0,
    latency_alert_threshold: float = 500.0,
    latency_critical_threshold: float = 1000.0,
    loss_warn_threshold: float = 0.00,
    loss_alert_threshold: float = 0.05,
    loss_critical_threshold: float = 0.25,
) -> Tuple[NSImage | None, str]:
    """Create a status dot icon based on latency and loss thresholds.

    This function generates a small NSImage icon (20x20 pixels) that displays
    a colored dot indicating the network status based on latency and packet
    loss values. The color changes according to configurable thresholds for
    warning, alert, and critical conditions.

    Args:
        latency (float | None): Network latency in milliseconds, or None if unavailable.
        loss (float | None): Packet loss as a decimal (0.0-1.0), or None if unavailable.
        last_state (str | None): The previous state of the network status ("normal", "warn", "alert", "critical", or "unknown"). Used to determine if the icon needs to be updated. Defaults to None.
        latency_warn_threshold (float): Warning threshold for latency in ms. Defaults to 80.0.
        latency_alert_threshold (float): Alert threshold for latency in ms. Defaults to 500.0.
        latency_critical_threshold (float): Critical threshold for latency in ms. Defaults to 1000.0.
        loss_warn_threshold (float): Warning threshold for loss as decimal. Defaults to 0.00.
        loss_alert_threshold (float): Alert threshold for loss as decimal. Defaults to 0.05.
        loss_critical_threshold (float): Critical threshold for loss as decimal. Defaults to 0.25.

    Returns:
        Tuple[NSImage | None, str]: A tuple with a 20x20 pixel icon with a colored dot representing network status, or None
        if the new state equals the previous state, and a string describing the current state.

    """

    symbol_name = "circle.fill"

    match (latency, loss):
        case (la, lo) if lo is None:
            symbol_name = "circle.dotted"
            color = None
            state = "unknown"
        case (la, lo) if (
            la or 0.0
        ) > latency_critical_threshold or lo > loss_critical_threshold:  # type: ignore[comparison-overlap]
            color = NSColor.redColor()
            state = "critical"
        case (la, lo) if (
            la or 0.0
        ) > latency_alert_threshold or lo > loss_alert_threshold:  # type: ignore[comparison-overlap]
            color = NSColor.orangeColor()
            state = "alert"
        case (la, lo) if (
            la or 0.0
        ) > latency_warn_threshold or lo > loss_warn_threshold:  # type: ignore[comparison-overlap]
            color = NSColor.yellowColor()
            state = "warn"
        case _:
            color = None
            state = "normal"

    if state == last_state:
        return None, state

    return (symbol_icon(symbol_name, "Network Status", color, True), state)


def status_text_icon(
    latency: float | None,
    loss: float | None,
    last_state: str | None = None,
    latency_warn_threshold: float = 80.0,
    latency_alert_threshold: float = 500.0,
    latency_critical_threshold: float = 1000.0,
    loss_warn_threshold: float = 0.00,
    loss_alert_threshold: float = 0.05,
    loss_critical_threshold: float = 0.25,
) -> Tuple[NSImage | None, str]:
    """Create a status text icon showing latency and loss with color-coded thresholds.

    This function generates a two-line NSImage icon displaying network latency
    and packet loss values. The background color changes based on configurable
    thresholds: normal (no background), warning (yellow), alert (orange), and
    critical (red).

    Args:
        latency (float | None): Network latency in milliseconds, or None if unavailable.
        loss (float | None): Packet loss as a decimal (0.0-1.0), or None if unavailable.
        last_state (str | None): The previous state of the network status (concatenation of latency and loss states). Used to determine if the icon needs to be updated. Defaults to None.
        latency_warn_threshold (float): Warning threshold for latency in ms. Defaults to 80.0.
        latency_alert_threshold (float): Alert threshold for latency in ms. Defaults to 500.0.
        latency_critical_threshold (float): Critical threshold for latency in ms. Defaults to 1000.0.
        loss_warn_threshold (float): Warning threshold for loss as decimal. Defaults to 0.00.
        loss_alert_threshold (float): Alert threshold for loss as decimal. Defaults to 0.05.
        loss_critical_threshold (float): Critical threshold for loss as decimal. Defaults to 0.25.

    Returns:
        Tuple[NSImage | None, str]: A tuple with a 50x20 pixel icon with right-aligned text showing latency and loss values, or None
        if the new state equals the previous state, and a string describing the current state.
    """

    latency_text = f"{latency:.1f}" if latency is not None else "---"
    loss_text = f"{loss * 100:.1f}" if loss is not None else "---"
    new_state = f"{latency_text}-{loss_text}"
    if new_state == last_state:
        return None, new_state

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

    for idx, (value, thresholds) in enumerate(
        ((loss, loss_thresholds), (latency, latency_thresholds))
    ):
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
                rect = NSMakeRect(0, (10 * idx), size.width, 10)
                NSColor.yellowColor().drawSwatchInRect_(rect)
            case v if v <= thresholds[2]:
                text_color = NSColor.blackColor()
                font = boldFont
                rect = NSMakeRect(0, (10 * idx), size.width, 10)
                NSColor.orangeColor().drawSwatchInRect_(rect)
            case _:
                text_color = NSColor.whiteColor()
                font = boldFont
                rect = NSMakeRect(0, (10 * idx), size.width, 10)
                NSColor.redColor().drawSwatchInRect_(rect)

        attributes = {
            NSForegroundColorAttributeName: text_color,
            NSFontAttributeName: font,
        }

        text = f"{value * (1 if idx else 100):.1f}" if value is not None else "---"
        text += " ms" if idx else " %"
        value_text = NSString.stringWithString_(text)
        value_size = value_text.sizeWithAttributes_(attributes)
        value_x = size.width - value_size.width - 2
        value_text.drawAtPoint_withAttributes_(
            (value_x - 4 + (4 * idx), (10 * idx)), attributes
        )

    image.unlockFocus()
    return image, new_state


def symbol_icon(
    symbol_name: str,
    accessibility_description: str,
    color: NSColor | None = None,
    small: bool = False,
) -> NSImage:
    """Create a template icon from an SF Symbol.

    This function creates a 20x20 pixel NSImage icon from the specified SF Symbol,
    suitable for use in macOS menu bars. The resulting image can optionally be
    colored and sized smaller for different display contexts.

    Args:
        symbol_name (str): The name of the SF Symbol (e.g., 'pause.circle').
        accessibility_description (str): Accessibility description for the icon.
        color (NSColor|None, optional): Color to apply to the symbol. If None,
                                       creates a template image for automatic theming.
                                       Defaults to None.
        small (bool, optional): If True, draws symbol in center 12x12 area for smaller
                               appearance. If False, fills entire 20x20 area.
                               Defaults to False.

    Returns:
        NSImage: A 20x20 pixel icon of the specified SF Symbol, optionally colored.
    """
    # Create SF Symbol image with configuration
    symbol_image = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
        symbol_name, accessibility_description
    )

    if color is not None:
        # Create a hierarchical color configuration and apply it to the symbol
        config = NSImageSymbolConfiguration.configurationWithHierarchicalColor_(color)
        symbol_image = symbol_image.imageWithSymbolConfiguration_(config)

    # Create a new 20x20 image
    size = NSSize(20, 20)
    image = NSImage.alloc().initWithSize_(size)

    image.lockFocus()

    # Draw the symbol image scaled to fit the 20x20 size
    if small:
        symbol_image.drawInRect_(NSMakeRect(4, 4, 12, 12))
    else:
        symbol_image.drawInRect_(NSMakeRect(0, 0, 20, 20))

    image.unlockFocus()
    if color is None:
        image.setTemplate_(True)

    return image
