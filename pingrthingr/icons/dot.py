"""Dot icon generation for PingrThingr.

Provides a small coloured-dot menu bar icon whose colour reflects the
worst-case criticality across latency and packet loss.
"""

from typing import Tuple
from .symbol import symbol_icon
from AppKit import (
    NSColor,  # type: ignore[import]
    NSImage,  # type: ignore[import]
)

def status_dot_icon(
    latency_criticality: int,
    loss_criticality: int,
    last_state: str | None = None,
) -> Tuple[NSImage | None, str]:
    """Create a coloured-dot status icon from pre-computed criticality levels.

    Generates a 20x20 pixel NSImage containing a filled circle whose colour
    reflects the worst-case criticality: normal (default tint), warning
    (yellow), alert (orange), or critical (red). An unknown state uses a
    dotted circle.

    Args:
        latency_criticality (int): Pre-computed criticality level for latency (0–4).
        loss_criticality (int): Pre-computed criticality level for packet loss (0–4).
        last_state (str | None): State string from the previous call; return value is
            ``None`` when the state is unchanged. Defaults to None.

    Returns:
        Tuple[NSImage | None, str]: A 20x20 pixel NSImage, or None if the state is
        unchanged, paired with a string describing the current state.
    """
    criticality = max(latency_criticality, loss_criticality)

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
