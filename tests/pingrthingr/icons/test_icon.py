from AppKit import (
    NSAppearance,  # type: ignore[import]
    NSAppearanceNameDarkAqua, # type: ignore[import]
    NSAppearanceNameAqua, # type: ignore[import]
    NSImage,  # type: ignore[import]
    NSImageView,  # type: ignore[import]
    NSView,  # type: ignore[import]
    NSMakeRect,  # type: ignore[import]
    NSPNGFileType,  # type: ignore[import]
)
from Quartz import CGColorCreate, CGColorSpaceCreateDeviceRGB  # type: ignore[import]
from pathlib import Path
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
    ("ok_latency", 50.0, 0.0),
    ("warn_loss", 0.0, 0.02),
    ("warn_edge_latency", 80.0, 0.0),
    ("warn_clear_latency", 100.0, 0.0),
    ("alert_edge_loss", 0.0, 0.05),
    ("alert_clear_loss", 0.0, 0.06),
    ("alert_edge_latency", 500.0, 0.0),
    ("alert_clear_latency", 600.0, 0.0),
    ("critical_edge_loss", 0.0, 0.25),
    ("critical_clear_loss", 0.0, 0.3),
    ("critical_edge_latency", 1000.0, 0.0),
    ("critical_clear_latency", 1001.0, 0.0),
]

colorspace = CGColorSpaceCreateDeviceRGB()
white = CGColorCreate(colorspace, (1, 1, 1, 1))
black = CGColorCreate(colorspace, (0, 0, 0, 1))

latency_thresholds = ThresholdModel(warn=80.0, alert=500.0, critical=1000.0)
loss_thresholds = ThresholdModel(warn=0.01, alert=0.05, critical=0.25)

def nsimage_to_nsview(ns_image: NSImage) -> NSView:
    size = ns_image.size()
    image_view = NSImageView.alloc().initWithFrame_(NSMakeRect(0, -size.height/2, size.width, size.height))
    image_view.setImage_(ns_image)
    outview = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, size.width, size.height))
    outview.addSubview_(image_view)
    return outview

def nsview_to_png(ns_view: NSView, path: str, dark: bool = False) -> None:
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


class TestIconImages:
    @pytest.mark.parametrize("dark", [True, False])
    @pytest.mark.parametrize("display", ["Text", "Dot"])
    @pytest.mark.parametrize("case, latency, loss", ping_thresholds)
    def test_status_icon(
        self, compare_image, case, latency, loss, display, dark
    ):
        # Skip visual testing for headless environments        
        icon, _ = generate_status_icon(display, latency=latency, loss=loss, latency_thresholds=latency_thresholds, loss_thresholds=loss_thresholds)
        assert (
            compare_image(
                icon, f"{display.lower()}-{case}-{'dark' if dark else 'light'}"
            , dark=dark)
            < 0.01
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
