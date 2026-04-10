from AppKit import (
    NSBitmapImageRep,  # type: ignore[import]
    NSCalibratedRGBColorSpace,  # type: ignore[import]
    NSColor,  # type: ignore[import]
    NSDeviceRGBColorSpace,  # type: ignore[import]
    NSGraphicsContext,  # type: ignore[import]
    NSImage,  # type: ignore[import]
    NSView,  # type: ignore[import]
    NSMakeRect,  # type: ignore[import]
    NSPNGFileType,  # type: ignore[import]
    NSRectFill,  # type: ignore[import]
)
from pathlib import Path
from typing import Literal
from unittest.mock import Mock
import pytest
from pingrthingr.settings import ThresholdModel
from pingrthingr.icons import (
    symbol_icon,
    status_dot_icon,
    status_text_icon,
    generate_status_icon,
)

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

latency_thresholds = ThresholdModel(warn=80.0, alert=500.0, critical=1000.0)
loss_thresholds = ThresholdModel(warn=0.01, alert=0.05, critical=0.25)

def nsview_to_nsimage(nsview: NSView, path: str) -> NSImage:
    viewbounds = nsview.bounds()
    newbounds = NSMakeRect(0, -viewbounds.size.height/2, viewbounds.size.width, viewbounds.size.height)
    bitmap_rep = nsview.bitmapImageRepForCachingDisplayInRect_(newbounds)
    nsview.cacheDisplayInRect_toBitmapImageRep_(newbounds, bitmap_rep)
    
    image = NSImage.alloc().initWithSize_(viewbounds.size)
    image.addRepresentation_(bitmap_rep)
    
    return image


def nsimage_to_png(ns_image: NSImage | NSView, path: str) -> None:
    """Write an NSImage to a PNG file without requiring a display context.

    For "retina" and "low", renders into an explicit off-screen NSBitmapImageRep
    at the target pixel dimensions via NSGraphicsContext, which works headlessly.
    For None, falls back to TIFFRepresentation() (highest resolution available).

    Args:
        ns_image: The NSImage to convert.
        path: Destination file path for the PNG.
    """

    if isinstance(ns_image, NSView):
        ns_image = nsview_to_nsimage(ns_image, path)

    logical_size = ns_image.size()
    pixel_w = int(logical_size.width * 2)
    pixel_h = int(logical_size.height * 2)

    bitmap_rep = NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
        None, pixel_w, pixel_h, 8, 4, True, False, NSCalibratedRGBColorSpace, 0, 0
    )
    ctx = NSGraphicsContext.graphicsContextWithBitmapImageRep_(bitmap_rep)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.setCurrentContext_(ctx)

    ns_image.drawInRect_(NSMakeRect(0, 0, pixel_w, pixel_h))
    NSGraphicsContext.restoreGraphicsState()

    png_data = bitmap_rep.representationUsingType_properties_(NSPNGFileType, None)
    png_data.writeToFile_atomically_(path, True)


@pytest.fixture
def compare_image(image_diff, tmp_path):
    def _test_image_diff(image: NSImage | NSView, test_name: str) -> float:
        exemplar_image = base_path / f"resources/example-{test_name}.png"
        output_path = tmp_path / f"compare-{test_name}.png"
        if not Path(exemplar_image).is_file():  # pragma: no cover
            nsimage_to_png(image, str(exemplar_image))

        nsimage_to_png(image, str(output_path))
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
    @pytest.mark.parametrize("case, latency, loss", ping_thresholds)
    def test_status_text_icon(
        self, compare_image, case, latency, loss
    ):
        # Skip visual testing for headless environments        
        text_icon, _ = status_text_icon(latency=latency, loss=loss, latency_thresholds=latency_thresholds, loss_thresholds=loss_thresholds)
        assert (
            compare_image(
                text_icon, f"text-{case}"
            )
            < 0.01
        ), "Generated icon should match reference image"

    @pytest.mark.parametrize("case, latency, loss", ping_thresholds)
    def test_status_dot_icon(self, compare_image, case, latency, loss):
        dot_icon, _ = status_dot_icon(
            latency=latency,
            loss=loss,
            latency_thresholds=latency_thresholds,
            loss_thresholds=loss_thresholds,
        )
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
        icon1, state1 = testfunction(
            latency=latency,
            loss=loss,
            last_state=None,
            latency_thresholds=latency_thresholds,
            loss_thresholds=loss_thresholds,
        )
        icon2, state2 = testfunction(
            latency=latency,
            loss=loss,
            last_state=state1,
            latency_thresholds=latency_thresholds,
            loss_thresholds=loss_thresholds,
        )
        assert icon1 is not None, "Icon should be generated on first call"
        assert icon2 is None, "Icon should not be regenerated if state is unchanged"
