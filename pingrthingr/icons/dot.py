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
