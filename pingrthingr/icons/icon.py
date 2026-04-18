"""Icon generation module for PingrThingr application.

This module provides functions to create NSImage icons for displaying
network status information in the macOS menu bar, including status text
with color-coded thresholds and SF Symbol icons.
"""

import logging

logger = logging.getLogger(__name__)

from AppKit import (
    CGRect,  # type: ignore[import]
    NSAppearance,  # type: ignore[import]
    NSAppearanceNameDarkAqua,  # type: ignore[import]
    NSImage,  # type: ignore[import]
    NSView,  # type: ignore[import]
    NSColor,  # type: ignore[import]
    NSTextField,  # type: ignore[import]
    NSMakeRect,  # type: ignore[import]
    NSSize,  # type: ignore[import]
    NSFont,  # type: ignore[import]
    NSImageSymbolConfiguration,  # type: ignore[import]
)
from typing import Tuple
from ..settings import ThresholdModel, IconStyle


def nsview_to_nsimage(nsview: NSView) -> NSImage:
    """Render an NSView into an NSImage by capturing its display output.

    Creates a bitmap representation of the view at its current size and
    wraps it in an NSImage. The view does not need to be attached to a
    window for this to work.

    Args:
        nsview (NSView): The view to capture.

    Returns:
        NSImage: A rasterised image of the view's contents.
    """
    bounds = nsview.bounds()
    bitmap_rep = nsview.bitmapImageRepForCachingDisplayInRect_(bounds)
    nsview.cacheDisplayInRect_toBitmapImageRep_(bounds, bitmap_rep)
    image = NSImage.alloc().initWithSize_(bounds.size)
    image.addRepresentation_(bitmap_rep)
    return image


def _criticality(
    latency: float | None,
    loss: float | None,
    latency_thresholds: ThresholdModel,
    loss_thresholds: ThresholdModel,
) -> Tuple[int, int]:
    """Evaluate the criticality level of latency and loss values.

    Compares latency and loss values against threshold models to determine
    criticality levels from 0 (unknown) to 4 (critical).

    Args:
        latency (float | None): Network latency in milliseconds, or None if unavailable.
        loss (float | None): Packet loss as a decimal (0.0-1.0), or None if unavailable.
        latency_thresholds (ThresholdModel): Threshold configuration for latency evaluation.
        loss_thresholds (ThresholdModel): Threshold configuration for loss evaluation.

    Returns:
        Tuple[int, int]: A tuple of (latency_criticality, loss_criticality) levels.
                        Each level is 0-4 where 0=unknown, 1=normal, 2=warn, 3=alert, 4=critical.
    """

    def _evaluate_criticality(value: float | None, thresholds: ThresholdModel) -> int:

        if value is None:  # pragma: no cover
            raise ValueError(
                "Cannot mix None values with numeric values for criticality evaluation"
            )

        match value:
            # Special case to allow any non-zero value to be considered a warning or higher, but treat 0.0 as normal
            case 0.0:
                return 1
            case v if v >= thresholds.critical:
                return 4
            case v if v >= thresholds.alert:
                return 3
            case v if v >= thresholds.warn:
                return 2
            case _:
                return 1

    if latency is None and loss is None:  # pragma: no cover
        return (0, 0)

    latency_criticality = _evaluate_criticality(latency, latency_thresholds)
    loss_criticality = _evaluate_criticality(loss, loss_thresholds)

    logger.debug(
        f"In _criticality(): Latency: {latency}, Loss: {loss}, Latency Criticality: {latency_criticality}, Loss Criticality: {loss_criticality}"
    )
    return latency_criticality, loss_criticality


def generate_status_icon(
    style: IconStyle,
    latency: float | None,
    loss: float | None,
    latency_thresholds: ThresholdModel,
    loss_thresholds: ThresholdModel,
    last_state: str | None = None,
    appearance: NSAppearance | None = None,
) -> Tuple[NSImage | NSView | None, str]:
    """Generate a status icon based on the specified style and network metrics.

    Creates either a dot or text icon representing network status based on latency
    and packet loss values. Returns None if the state hasn't changed to avoid
    unnecessary updates.

    Args:
        style (IconStyle): The icon style to generate ('Dot' or 'Text').
        latency (float | None): Network latency in milliseconds, or None if unavailable.
        loss (float | None): Packet loss as a decimal (0.0-1.0), or None if unavailable.
        latency_thresholds (ThresholdModel): Threshold configuration for latency evaluation.
        loss_thresholds (ThresholdModel): Threshold configuration for loss evaluation.
        last_state (str | None): The previous state to compare against. Defaults to None.

    Returns:
        Tuple[NSImage | NSView | None, str]: A tuple containing the icon (NSImage for dot,
                                            NSView for text, or None if unchanged) and
                                            the current state string.

    Raises:
        NotImplementedError: If an unsupported icon style is requested.
    """

    match style:
        case "Dot":
            icon, state = status_dot_icon(
                latency,
                loss,
                latency_thresholds,
                loss_thresholds,
                last_state,
            )
        case "Text":
            icon, state = status_text_icon(
                latency,
                loss,
                latency_thresholds,
                loss_thresholds,
                last_state,
                appearance,
            )
        case _:  # pragma: no cover
            raise NotImplemented(f"No implementation for icon style: {style}")
    return icon, state


def status_dot_icon(
    latency: float | None,
    loss: float | None,
    latency_thresholds: ThresholdModel,
    loss_thresholds: ThresholdModel,
    last_state: str | None = None,
) -> Tuple[NSImage | None, str]:
    """Create a status dot icon based on latency and loss thresholds.

    This function generates a small NSImage icon (20x20 pixels) that displays
    a colored dot indicating the network status based on latency and packet
    loss values. The color changes according to configurable thresholds for
    warning, alert, and critical conditions.

    Args:
        latency (float | None): Network latency in milliseconds, or None if unavailable.
        loss (float | None): Packet loss as a decimal (0.0-1.0), or None if unavailable.
        latency_thresholds (ThresholdModel): Threshold configuration for latency evaluation.
        loss_thresholds (ThresholdModel): Threshold configuration for loss evaluation.
        last_state (str | None): The previous state string returned by the last call to avoid unnecessary updates. Defaults to None.

    Returns:
        Tuple[NSImage | None, str]: A tuple with a 20x20 pixel icon with a colored dot representing network status, or None
        if the new state equals the previous state, and a string describing the current state.

    """
    criticality = max(_criticality(latency, loss, latency_thresholds, loss_thresholds))

    symbol_name = "circle.dotted" if criticality == 0 else "circle.fill"

    match criticality:
        case 0:
            color = None
            state = "unknown"
        case 1:
            color = None
            state = "normal"
        case 2:
            color = NSColor.yellowColor()
            state = "warn"
        case 3:
            color = NSColor.orangeColor()
            state = "alert"
        case 4:
            color = NSColor.redColor()
            state = "critical"
        case _:  # pragma: no cover
            raise ValueError(f"Invalid criticality level: {criticality}")

    if state == last_state:
        return None, state

    return (symbol_icon(symbol_name, "Network Status", color, True), state)


def status_text_icon(
    latency: float | None,
    loss: float | None,
    latency_thresholds: ThresholdModel,
    loss_thresholds: ThresholdModel,
    last_state: str | None = None,
    appearance: NSAppearance | None = None,
) -> Tuple[NSView | None, str]:
    """Create a status text icon showing latency and loss with color-coded thresholds.

    This function generates a two-line NSView icon (50x22 pixels) displaying network latency
    and packet loss values. Each line's background color changes based on configurable
    thresholds: normal (no background), warning (yellow), alert (orange), and
    critical (red).

    Args:
        latency (float | None): Network latency in milliseconds, or None if unavailable.
        loss (float | None): Packet loss as a decimal (0.0-1.0), or None if unavailable.
        latency_thresholds (ThresholdModel): Threshold configuration for latency evaluation.
        loss_thresholds (ThresholdModel): Threshold configuration for loss evaluation.
        last_state (str | None): The previous state string returned by the last call to avoid unnecessary updates. Defaults to None.


    Returns:
        Tuple[NSView | None, str]: A tuple with a 50x22 pixel NSView or None, and a string describing the current state.
    """

    latency_text = f"{latency:.1f} ms" if latency is not None else "---"
    loss_text = f"{loss * 100:.1f} %" if loss is not None else "---"
    new_state = f"{latency_text}-{loss_text}"
    if new_state == last_state:
        return None, new_state

    size = NSSize(50, 22)

    # Set up fonts
    normalFont = NSFont.systemFontOfSize_(9)
    boldFont = NSFont.boldSystemFontOfSize_(9)

    latency_criticality, loss_criticality = _criticality(
        latency, loss, latency_thresholds, loss_thresholds
    )

    view = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, size.width, size.height))

    def _value_view(text: str, criticality: int, frame: CGRect) -> NSView:
        """Create an NSTextField view for displaying status text with appropriate styling.

        Args:
            text (str): The text to display in the field.
            criticality (int): Criticality level (1-4) determining background color and font weight.
            frame (CGRect): The frame rectangle for positioning the text field.

        Returns:
            NSView: An NSTextField configured with appropriate text, colors, and positioning.
        """

        text_view = NSTextField.labelWithString_(text)
        text_view.setAlignment_(2)  # right align
        if criticality <= 1:
            text_view.setFont_(normalFont)
        else:
            text_view.setFont_(boldFont)
            text_view.setDrawsBackground_(True)

            match criticality:
                case 2:
                    text_view.setBackgroundColor_(NSColor.yellowColor())
                    text_view.setTextColor_(NSColor.blackColor())
                case 3:
                    text_view.setBackgroundColor_(NSColor.orangeColor())
                    text_view.setTextColor_(NSColor.blackColor())
                case 4:
                    text_view.setBackgroundColor_(NSColor.redColor())
                    text_view.setTextColor_(NSColor.whiteColor())
                case _:  # pragma: no cover
                    raise ValueError(f"Invalid criticality level: {criticality}")

        text_view.setFrame_(frame)
        return text_view

    latency_view = _value_view(
        latency_text,
        latency_criticality,
        NSMakeRect(0, size.height / 2, size.width, size.height / 2),
    )
    loss_view = _value_view(
        loss_text,
        loss_criticality,
        NSMakeRect(0, 0, size.width, size.height / 2),
    )

    view.addSubview_(latency_view)
    view.addSubview_(loss_view)

    view.setAppearance_(appearance)

    image = nsview_to_nsimage(view)
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
