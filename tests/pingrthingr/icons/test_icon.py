from AppKit import (
    NSBitmapImageRep,  # type: ignore[import]
    NSCalibratedRGBColorSpace,  # type: ignore[import]
    NSAppearance,  # type: ignore[import]
    NSAppearanceNameDarkAqua, # type: ignore[import]
    NSAppearanceNameAqua, # type: ignore[import]
    NSColor,  # type: ignore[import]
    NSDeviceRGBColorSpace,  # type: ignore[import]
    NSGraphicsContext,  # type: ignore[import]
    NSImage,  # type: ignore[import]
    NSImageView,  # type: ignore[import]
    NSView,  # type: ignore[import]
    NSMakeRect,  # type: ignore[import]
    NSPNGFileType,  # type: ignore[import]
    NSRectFill,  # type: ignore[import]
)
from Quartz import CGColorCreate, CGColorSpaceCreateDeviceRGB  # type: ignore[import]
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

colorspace = CGColorSpaceCreateDeviceRGB()
white = CGColorCreate(colorspace, (1, 1, 1, 1))
black = CGColorCreate(colorspace, (0, 0, 0, 1))

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

def nsimage_to_nsview(ns_image: NSImage) -> NSView:
    size = ns_image.size()
    image_view = NSImageView.alloc().initWithFrame_(NSMakeRect(0, -size.height/2, size.width, size.height))
    image_view.setImage_(ns_image)
    outview = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, size.width, size.height))
    outview.addSubview_(image_view)
    return outview

def nsview_to_png(ns_view: NSView, path: str, dark: bool = False) -> None:
    """Write an NSView to a PNG file without requiring a display context.

    Renders the view into an explicit off-screen NSBitmapImageRep at the target pixel dimensions via NSGraphicsContext, which works headlessly.

    Args:
        ns_view: The NSView to convert.

    """

    if isinstance(ns_view, NSImage):
        ns_view = nsimage_to_nsview(ns_view)

    viewbounds = ns_view.bounds()
    dark_aqua = NSAppearance.appearanceNamed_(NSAppearanceNameDarkAqua)
    light_aqua = NSAppearance.appearanceNamed_(NSAppearanceNameAqua)
    outview = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, viewbounds.size.width, viewbounds.size.height))
    outview.setWantsLayer_(True)
    outview.layer().setBackgroundColor_((black if dark else white))
    ns_view.setAppearance_(dark_aqua if dark else light_aqua)
    outview.addSubview_(ns_view)
    ns_view.setFrameOrigin_((0, viewbounds.size.height/2))
    bitmap_rep = outview.bitmapImageRepForCachingDisplayInRect_(viewbounds)
    outview.cacheDisplayInRect_toBitmapImageRep_(viewbounds, bitmap_rep)
    
    png_data = bitmap_rep.representationUsingType_properties_(NSPNGFileType, None)
    png_data.writeToFile_atomically_(path, True)

def test_foo():
    text_icon, _ = status_text_icon(
        latency=10,
        loss=0.0,
        latency_thresholds=latency_thresholds,
        loss_thresholds=loss_thresholds,
    )
    nsview_to_png(text_icon, "output.png", False)


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
        ns_image = nsimage_to_nsview(ns_image)

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
    def _test_image_diff(image: NSImage | NSView, test_name: str, dark: bool) -> float:
        exemplar_image = base_path / f"resources/example-{test_name}.png"
        output_path = tmp_path / f"compare-{test_name}.png"
        if not Path(exemplar_image).is_file():  # pragma: no cover
            nsview_to_png(image, str(exemplar_image), dark)

        nsview_to_png(image, str(output_path), dark)
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
    @pytest.mark.parametrize("dark", [True, False])
    @pytest.mark.parametrize("case, latency, loss", ping_thresholds)
    def test_status_text_icon(
        self, compare_image, case, latency, loss, dark
    ):
        # Skip visual testing for headless environments        
        text_icon, _ = status_text_icon(latency=latency, loss=loss, latency_thresholds=latency_thresholds, loss_thresholds=loss_thresholds)
        assert (
            compare_image(
                text_icon, f"text-{case}-{'dark' if dark else 'light'}"
            , dark=dark)
            < 0.01
        ), "Generated icon should match reference image"

    @pytest.mark.parametrize("dark", [True, False])
    @pytest.mark.parametrize("case, latency, loss", ping_thresholds)
    def test_status_dot_icon(self, compare_image, case, latency, loss, dark):
        dot_icon, _ = status_dot_icon(
            latency=latency,
            loss=loss,
            latency_thresholds=latency_thresholds,
            loss_thresholds=loss_thresholds,
        )
        assert (
            compare_image(dot_icon, f"dot-{case}-{'dark' if dark else 'light'}", dark=dark) < 0.01
        ), "Generated icon should match reference image"

    @pytest.mark.parametrize("dark", [True, False])
    def test_pause_icon(self, compare_image, dark):
        pause_icon = symbol_icon("pause.circle", "Paused")
        assert (
            compare_image(pause_icon, f"pause-{'dark' if dark else 'light'}", dark=dark) < 0.01
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
        icon2, _ = testfunction(
            latency=latency,
            loss=loss,
            last_state=state1,
            latency_thresholds=latency_thresholds,
            loss_thresholds=loss_thresholds,
        )
        assert icon1 is not None, "Icon should be generated on first call"
        assert icon2 is None, "Icon should not be regenerated if state is unchanged"
