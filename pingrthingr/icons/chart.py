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
    NSImage,  # type: ignore[import]
    NSMakeRect,  # type: ignore[import]
    NSSize,  # type: ignore[import]
    NSView,  # type: ignore[import]
)
from re import match as re_match
from .util import _nsview_to_nsimage, warn_color, alert_color, critical_color

def status_chart_icon(
    latency: float | None,
    loss: float | None,
    latency_criticality: int,
    loss_criticality: int,
    minimum_latency_scale: float,
    minimum_loss_scale: float,
    last_state: str | None = None,
    # appearance: NSAppearance | None = None,
    force: bool = False,
) -> Tuple[NSImage | None, NSView | None, str]:
    """Create a status chart icon showing latency and loss history with colour-coded criticality.

    Generates a menu bar icon up to (HISTORY_LENGTH * 4) x 22 pixels containing
    side-by-side bar charts for latency (top row) and packet loss (bottom row).
    Each bar's colour reflects its criticality level: unknown (grey), normal
    (label colour / template), warning (yellow), alert (orange), or critical (red).

    Normal-criticality bars are placed in a template NSImage (base_image) so they
    inherit system tinting. Colour-coded bars are returned as a separate NSView
    (overlay_view) that is composited on top in the menu bar.

    Args:
        latency (float | None): Latest network latency in milliseconds, or None if
            unavailable.
        loss (float | None): Latest packet loss as a decimal (0.0-1.0), or None if
            unavailable.
        latency_criticality (int): Pre-computed criticality level for latency (0-4).
        loss_criticality (int): Pre-computed criticality level for packet loss (0-4).
        minimum_latency_scale (float): Minimum value used as the full-height scale for
            the latency chart, preventing bars from appearing too tall on low values.
        minimum_loss_scale (float): Minimum value used as the full-height scale for
            the loss chart.
        last_state (str | None): Encoded state string from the previous call used to
            carry forward history. Return images are None when state is unchanged.
            Defaults to None.
        force (bool): If True, forces regeneration regardless of state. Defaults to False.

    Returns:
        Tuple[NSImage | None, NSView | None, str]: A tuple of (base_image, overlay_view,
        state_string). base_image is a template NSImage of the normal-criticality bars,
        or None if unchanged. overlay_view contains the colour-coded bars, or None if
        unchanged. state_string encodes the full bar history.
    """

    HISTORY_LENGTH = 12

    if last_state and re_match(r"chart-((\d+.\d+,\d+.\d+,\d+,\d+)(;|$))+", last_state):
        states = [
            (float(v[0]), float(v[1]), int(v[2]), int(v[3]))
            for v in [pair.split(",") for pair in last_state[6:].split(";")]
        ]
    else:
        states = []

    if not force:
        states.insert(
            0,
            (
                latency if latency is not None else 0,
                loss if loss is not None else 0,
                latency_criticality,
                loss_criticality,
            ),
        )

    states = states[:HISTORY_LENGTH]

    # state format: "chart-" followed by tuples of latency/loss floats, and a criticality integers. Values are separated
    # by a comma, tuples are separated by a semicolon. Most recent tuple is first.

    new_state = (
        f"chart-{';'.join([f'{x[0]:.2f},{x[1]:.2f},{x[2]},{x[3]}' for x in states])}"
    )

    size = NSSize((HISTORY_LENGTH * 4), 22)

    base_view = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, size.width, size.height))
    overlay_view = NSView.alloc().initWithFrame_(
        NSMakeRect(0, 0, size.width, size.height)
    )

    def _chart_view(
        states: List[Tuple[float, int]], min_scale: float, frame: CGRect
    ) -> Tuple[NSView, NSView]:
        """Build base and overlay NSViews for one row of the chart.

        Iterates over historical (value, criticality) pairs and creates a vertical
        bar for each. Bars at normal criticality go into the base view (template);
        all others go into the overlay view (fixed colour). A thin placeholder bar
        is added at the left edge when fewer than HISTORY_LENGTH samples are available.

        Args:
            states (List[Tuple[float, int]]): Ordered list of (value, criticality)
                tuples, most-recent first.
            min_scale (float): Minimum full-height scale; prevents bars from being
                disproportionately tall when actual values are small.
            frame (CGRect): Bounding rectangle for this chart row.

        Returns:
            Tuple[NSView, NSView]: (chart_base_view, chart_overlay_view) — the
            template-rendered base layer and the colour-coded overlay layer.
        """

        max_value = max((s[0] for s in states), default=0)
        max_scale = max(
            max_value, min(min_scale, max_value * 3)
        )  # Ensure some headroom above the max value for better visualization
        logger.debug(f"Max value for chart scaling: {max_scale}")
        chart_base_view = NSView.alloc().initWithFrame_(frame)
        chart_overlay_view = NSView.alloc().initWithFrame_(frame)

        for idx, (value, criticality) in enumerate(states):
            bar_height = (value / max_scale) * frame.size.height if max_scale > 0 else 0
            value_bar = NSBox.alloc().initWithFrame_(
                NSMakeRect(frame.size.width - (4 * (idx + 1)), 0, 4, max(bar_height, 1))
            )
            value_bar.setBoxType_(NSBoxCustom)
            value_bar.setBorderWidth_(0)
            match criticality:
                case 0:
                    value_bar.setFillColor_(NSColor.grayColor())
                    chart_overlay_view.addSubview_(value_bar)
                case 1:
                    value_bar.setFillColor_(NSColor.labelColor())
                    chart_base_view.addSubview_(value_bar)
                case 2:
                    value_bar.setFillColor_(warn_color)
                    chart_overlay_view.addSubview_(value_bar)
                case 3:
                    value_bar.setFillColor_(alert_color)
                    chart_overlay_view.addSubview_(value_bar)
                case 4:
                    value_bar.setFillColor_(critical_color)
                    chart_overlay_view.addSubview_(value_bar)
                case _:  # pragma: no cover
                    raise ValueError(f"Invalid criticality level: {criticality}")

        if len(states) < HISTORY_LENGTH:
            blank_bars = HISTORY_LENGTH - len(states)
            for i in range(blank_bars):
                empty_bar = NSBox.alloc().initWithFrame_(
                    NSMakeRect(i * 4, 0, 2, 1)
                )
                empty_bar.setBoxType_(NSBoxCustom)
                empty_bar.setFillColor_(NSColor.grayColor())
                empty_bar.setBorderWidth_(0)
                chart_overlay_view.addSubview_(empty_bar)
        return chart_base_view, chart_overlay_view

    latency_base_view, latency_overlay_view = _chart_view(
        [(x[0], x[2]) for x in states],
        minimum_latency_scale,
        NSMakeRect(0, size.height / 2, size.width, size.height / 2),
    )

    loss_base_view, loss_overlay_view = _chart_view(
        [(x[1], x[3]) for x in states],
        minimum_loss_scale,
        NSMakeRect(0, 0, size.width, size.height / 2),
    )

    base_view.addSubview_(latency_base_view)
    overlay_view.addSubview_(latency_overlay_view)
    base_view.addSubview_(loss_base_view)
    overlay_view.addSubview_(loss_overlay_view)

    base_image = _nsview_to_nsimage(base_view)
    base_image.setTemplate_(True)
    return base_image, overlay_view, new_state
