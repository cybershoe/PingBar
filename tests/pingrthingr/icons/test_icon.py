from AppKit import (
    NSBitmapImageRep,  # type: ignore[import]
    NSCalibratedRGBColorSpace,  # type: ignore[import]
    NSColor,  # type: ignore[import]
    NSDeviceRGBColorSpace,  # type: ignore[import]
    NSGraphicsContext,  # type: ignore[import]
    NSImage,  # type: ignore[import]
    NSMakeRect,  # type: ignore[import]
    NSPNGFileType,  # type: ignore[import]
    NSRectFill,  # type: ignore[import]
)
from pathlib import Path
from typing import Literal
from unittest.mock import Mock
import pytest
from pingrthingr.icons import symbol_icon, status_dot_icon, status_text_icon

base_path = Path(__file__).parent

ping_thresholds = [
    ("unknown", None, None),
    ("no_loss", 0.0, 0.0),
    ("warn_loss", 0.0, 0.02),
    ("warn_latency", 100.0, 0.0),
    ("alert_loss", 0.0, 0.06),
    ("alert_latency", 600.0, 0.0),
    ("critical_loss", 0.0, 0.3),
    ("critical_latency", 1001.0, 0.0),
]


def nsimage_to_png(ns_image: NSImage, path: str, dark: bool = False) -> None:
    """Write an NSImage to a PNG file without requiring a display context.

    For "retina" and "low", renders into an explicit off-screen NSBitmapImageRep
    at the target pixel dimensions via NSGraphicsContext, which works headlessly.
    For None, falls back to TIFFRepresentation() (highest resolution available).

    Args:
        ns_image: The NSImage to convert.
        path: Destination file path for the PNG.
    """

    logical_size = ns_image.size()
    pixel_w = int(logical_size.width * 2)
    pixel_h = int(logical_size.height * 2)

    bitmap_rep = NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
        None, pixel_w, pixel_h, 8, 4, True, False, NSCalibratedRGBColorSpace, 0, 0
    )
    ctx = NSGraphicsContext.graphicsContextWithBitmapImageRep_(bitmap_rep)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.setCurrentContext_(ctx)
    if dark:
        NSColor.blackColor().setFill()
    else:
        NSColor.whiteColor().setFill()
    NSRectFill(NSMakeRect(0, 0, pixel_w, pixel_h))
    ns_image.drawInRect_(NSMakeRect(0, 0, pixel_w, pixel_h))
    NSGraphicsContext.restoreGraphicsState()

    png_data = bitmap_rep.representationUsingType_properties_(NSPNGFileType, None)
    png_data.writeToFile_atomically_(path, True)


@pytest.fixture
def compare_image(image_diff, tmp_path):
    def _test_image_diff(image: NSImage, test_name: str, dark: bool = False) -> float:
        exemplar_image = base_path / f"resources/example-{test_name}.png"
        output_path = tmp_path / f"compare-{test_name}.png"
        if not Path(exemplar_image).is_file():  # pragma: no cover
            nsimage_to_png(image, str(exemplar_image), dark=dark)
        nsimage_to_png(image, str(output_path), dark=dark)
        return image_diff(str(output_path), str(exemplar_image))

    return _test_image_diff


@pytest.fixture
def mock_darkmode(request, mocker):
    mock_defaults = mocker.MagicMock()
    mock_defaults.stringForKey_.return_value = request.param
    mock_ns_user_defaults = mocker.MagicMock()
    mock_ns_user_defaults.standardUserDefaults.return_value = mock_defaults
    mock = mocker.patch("pingrthingr.icons.icon.NSUserDefaults", mock_ns_user_defaults)
    return mock


class TestIconImages:
    @pytest.mark.parametrize(
        "mock_darkmode, darkmode",
        [("Light",) * 2, ("Dark",) * 2],
        indirect=["mock_darkmode"],
    )
    @pytest.mark.parametrize("case, latency, loss", ping_thresholds)
    def test_status_text_icon(
        self, compare_image, mock_darkmode, darkmode, case, latency, loss
    ):
        text_icon, _ = status_text_icon(latency=latency, loss=loss)
        assert (
            compare_image(
                text_icon, f"text-{case}-{darkmode}", dark=(darkmode == "Dark")
            )
            < 0.01
        ), "Generated icon should match reference image"

    @pytest.mark.parametrize("case, latency, loss", ping_thresholds)
    def test_status_dot_icon(self, compare_image, case, latency, loss):
        dot_icon, _ = status_dot_icon(latency=latency, loss=loss)
        assert (
            compare_image(dot_icon, f"dot-{case}") < 0.01
        ), "Generated icon should match reference image"

    def test_pause_icon(self, compare_image):
        pause_icon = symbol_icon("pause.circle", "Paused")
        assert (
            compare_image(pause_icon, "pause") < 0.01
        ), "Generated pause icon should match reference image"


class TestIconSameState:
    @pytest.mark.parametrize("testfunction", [status_dot_icon, status_text_icon])
    @pytest.mark.parametrize("case, latency, loss", ping_thresholds)
    def test_status_icon_same_state(self, testfunction, case, latency, loss):
        icon1, state1 = testfunction(latency=latency, loss=loss, last_state=None)
        icon2, state2 = testfunction(latency=latency, loss=loss, last_state=state1)
        assert icon1 is not None, "Icon should be generated on first call"
        assert icon2 is None, "Icon should not be regenerated if state is unchanged"
