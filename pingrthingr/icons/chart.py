"""Chart icon generation for PingrThingr.

Provides a two-line menu bar icon that displays bar charts representing
latency and loss over time, with bar colours reflecting criticality levels.
"""
import logging

logger = logging.getLogger(__name__)

from typing import Tuple, List
from AppKit import (
    CGRect,  # type: ignore[import]
    NSBox,  # type: ignore[import]
    NSBoxCustom,  # type: ignore[import]
    NSColor,  # type: ignore[import]
    NSFont,  # type: ignore[import]
    NSImage,  # type: ignore[import]
    NSMakeRect,  # type: ignore[import]
    NSSize,  # type: ignore[import]
    NSView,  # type: ignore[import]
    NSAppearance,  # type: ignore[import]
)
from re import match as re_match
from .util import _nsview_to_nsimage


def status_chart_icon(
    latency: float | None,
    loss: float | None,
    latency_criticality: int,
    loss_criticality: int,
    minimum_latency_scale: float,
    minimum_loss_scale: float,
    last_state: str | None = None,
    appearance: NSAppearance | None = None,
) -> Tuple[NSImage | None, str]:
    """Create a status chart icon showing latency and loss with colour-coded criticality.

    Generates a 50x22 pixel two-line menu bar icon displaying bar charts for latency and
    packet loss values. Each bar's colour reflects its criticality level:
    normal (no background), warning (yellow), alert (orange), or critical (red).

    Args:
        latency (float | None): Network latency in milliseconds, or None if unavailable.
        loss (float | None): Packet loss as a decimal (0.0-1.0), or None if unavailable.
        latency_criticality (int): Pre-computed criticality level for latency (0-4).
        loss_criticality (int): Pre-computed criticality level for packet loss (0-4).
        last_state (str | None): State string from the previous call; return value is
            ``None`` when the state is unchanged. Defaults to None.
        appearance (NSAppearance | None): The NSAppearance to apply to the rendered view,
            or None to use the default appearance. Defaults to None.

    Returns:
        Tuple[NSImage | None, str]: A 50x22 pixel NSImage, or None if the state is
        unchanged, paired with a string describing the current state.
    """

    HISTORY_LENGTH = 12

    latency_text = f"{latency:.1f} ms" if latency is not None else "---"
    loss_text = f"{loss * 100:.1f} %" if loss is not None else "---"

    if last_state and re_match(r"chart-((\d+.\d+,\d+.\d+,\d+,\d+)(;|$))+", last_state):
        states = [(float(v[0]), float(v[1]), int(v[2]), int(v[3])) for v in [pair.split(",") for pair in last_state[6:].split(";")]]
    else:
        states = []

    
    states.insert(0, (latency if latency is not None else 0, loss if loss is not None else 0, latency_criticality, loss_criticality))
    

    # state format: "chart-" followed by tuples of latency/loss floats, and a criticality integers. Values are separated
    # by a comma, tuples are separated by a semicolon. Most recent tuple is first.


    new_state = f"chart-{';'.join([f'{x[0]:.2f},{x[1]:.2f},{x[2]},{x[3]}' for x in states[-HISTORY_LENGTH-1:]])}"

    size = NSSize((HISTORY_LENGTH * 4)+2, 22)

    view = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, size.width, size.height))

    def _chart_view(states: List[Tuple[float, int]], min_scale: float, frame: CGRect) -> NSView:

        max_value = max((s[0] for s in states), default=0)
        max_scale = max(max_value, min(min_scale, max_value * 3))  # Ensure some headroom above the max value for better visualization
        logger.debug(f"Max value for chart scaling: {max_scale}")
        chart_view = NSView.alloc().initWithFrame_(frame)

        left_bar = NSBox.alloc().initWithFrame_(
                NSMakeRect(frame.size.width - 1, 0, 1, frame.size.height)
            )
        left_bar.setBoxType_(NSBoxCustom)
        left_bar.setFillColor_(NSColor.grayColor())
        left_bar.setBorderWidth_(0)
        chart_view.addSubview_(left_bar)
        right_bar = NSBox.alloc().initWithFrame_(
                NSMakeRect(0, 0, 1, frame.size.height)
            )
        right_bar.setBoxType_(NSBoxCustom)
        right_bar.setFillColor_(NSColor.grayColor())
        right_bar.setBorderWidth_(0)
        chart_view.addSubview_(right_bar)

        for idx, (value, criticality) in enumerate(states):
            bar_height = (value / max_scale) * frame.size.height if max_scale > 0 else 0
            value_bar = NSBox.alloc().initWithFrame_(
                NSMakeRect(frame.size.width - (4 * (idx + 1)) - 1, 0, 4, max(bar_height, 1))
            )
            value_bar.setBoxType_(NSBoxCustom)
            match criticality:
                case 0:
                    value_bar.setFillColor_(NSColor.grayColor())
                case 1:
                    value_bar.setFillColor_(NSColor.labelColor())
                case 2:
                    value_bar.setFillColor_(NSColor.yellowColor())
                case 3:
                    value_bar.setFillColor_(NSColor.orangeColor())
                case 4:
                    value_bar.setFillColor_(NSColor.redColor())
                case _:  # pragma: no cover
                    raise ValueError(f"Invalid criticality level: {criticality}")
            value_bar.setBorderWidth_(0)
            chart_view.addSubview_(value_bar)

        return chart_view

    latency_view = _chart_view(
        [(x[0], x[2]) for x in states],
        minimum_latency_scale,
        NSMakeRect(0, size.height / 2, size.width, size.height / 2),
    )

    loss_view = _chart_view(
        [(x[1], x[3]) for x in states],
        minimum_loss_scale,
        NSMakeRect(0, 0, size.width, size.height / 2),
    )

    view.addSubview_(latency_view)
    view.addSubview_(loss_view)

    view.setAppearance_(appearance)

    image = _nsview_to_nsimage(view)
    return image, new_state
