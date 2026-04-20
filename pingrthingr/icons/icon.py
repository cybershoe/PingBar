"""Icon generation module for PingrThingr application.

This module provides functions to create NSImage icons for displaying
network status information in the macOS menu bar, including status text
with color-coded thresholds and SF Symbol icons.
"""

import logging

logger = logging.getLogger(__name__)

from AppKit import (
    NSAppearance,  # type: ignore[import]
    NSImage,  # type: ignore[import]
)
from typing import Tuple
from .dot import status_dot_icon
from .text import status_text_icon
from ..settings import ThresholdModel, IconStyle


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

        match value:
            # Special case to allow any non-zero value to be considered a warning or higher, but treat 0.0 as normal
            case None:
                return 0
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
) -> Tuple[NSImage | None, str]:
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

    latency_criticality, loss_criticality = _criticality(
        latency, loss, latency_thresholds, loss_thresholds
    )
    match style:
        case "Dot":
            icon, state = status_dot_icon(
                latency_criticality,
                loss_criticality,
                last_state,
            )
        case "Text":
            icon, state = status_text_icon(
                latency,
                loss,
                latency_criticality,
                loss_criticality,
                last_state,
                appearance,
            )
        case _:  # pragma: no cover
            raise NotImplemented(f"No implementation for icon style: {style}")
    return icon, state
