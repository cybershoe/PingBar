from typing import Tuple
from AppKit import (
    CGRect,  # type: ignore[import]
    NSColor,  # type: ignore[import]
    NSFont,  # type: ignore[import]
    NSImage,  # type: ignore[import]
    NSMakeRect,  # type: ignore[import]
    NSSize,  # type: ignore[import]
    NSView,  # type: ignore[import]
    NSAppearance,  # type: ignore[import]
    NSTextField,  # type: ignore[import]
)
from .util import _nsview_to_nsimage

def status_text_icon(
    latency: float | None,
    loss: float | None,
    latency_criticality: int,
    loss_criticality: int,
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

    # latency_criticality, loss_criticality = _criticality(
    #     latency, loss, latency_thresholds, loss_thresholds
    # )

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


    image = _nsview_to_nsimage(view)
    return image, new_state
