from AppKit import (
    NSAppearance,  # type: ignore[import]
    NSAppearanceNameDarkAqua,  # type: ignore[import]
    NSAppearanceNameAqua,  # type: ignore[import]
    NSBox,  # type: ignore[import]
    NSBoxCustom,  # type: ignore[import]
    NSColor,  # type: ignore[import]
    NSImage,  # type: ignore[import]
    NSImageView,  # type: ignore[import]
    NSMakeRect,  # type: ignore[import]
    NSView,  # type: ignore[import]
    NSPNGFileType,  # type: ignore[import]
)
from Quartz import CGColorCreate, CGColorSpaceCreateDeviceRGB  # type: ignore[import]
from pathlib import Path
import pytest
from pingrthingr.settings import ThresholdModel
from pingrthingr.icons import (
    symbol_icon,
    generate_status_icon,
)

base_path = Path(__file__).parent

ping_thresholds = [
    ("unknown", None, None),
    ("no_loss", 0.0, 0.0),
    ("full_loss", None, 1.0),
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


def flaatten_icon_to_png(
    nsimage: NSImage,
    output_path: Path,
    dark: bool = False,
    nsview: NSView | None = None,
) -> None:
    size = nsimage.size()
    frame = NSMakeRect(0, 0, size.width, size.height)
    flattened_view = NSView.alloc().initWithFrame_(frame)
    appearance = NSAppearance.appearanceNamed_(
        NSAppearanceNameDarkAqua if dark else NSAppearanceNameAqua
    )
    flattened_view.setAppearance_(appearance)

    bg_color = NSColor.blackColor() if dark else NSColor.whiteColor()
    background = NSBox.alloc().initWithFrame_(frame)
    background.setBoxType_(NSBoxCustom)
    background.setFillColor_(bg_color)
    background.setBorderWidth_(0)
    flattened_view.addSubview_(background)

    image_view = NSImageView.alloc().initWithFrame_(frame)
    image_view.setImage_(nsimage)
    flattened_view.addSubview_(image_view)

    if nsview is not None:
        flattened_view.addSubview_(nsview)

    bounds = flattened_view.bounds()
    bitmap_rep = None

    def draw_in_appearance():
        nonlocal bitmap_rep
        bitmap_rep = flattened_view.bitmapImageRepForCachingDisplayInRect_(bounds)
        flattened_view.cacheDisplayInRect_toBitmapImageRep_(bounds, bitmap_rep)

    appearance.performAsCurrentDrawingAppearance_(draw_in_appearance)
    png_data = bitmap_rep.representationUsingType_properties_(NSPNGFileType, None)  # type: ignore
    png_data.writeToFile_atomically_(str(output_path), True)


@pytest.fixture
def compare_image(image_diff, tmp_path):
    def _test_image_diff(
        image: NSImage, test_name: str, dark: bool = False, nsview: NSView | None = None
    ) -> float:
        exemplar_image = base_path / f"resources/example-{test_name}.png"
        output_path = tmp_path / f"compare-{test_name}.png"
        if not Path(exemplar_image).is_file():  # pragma: no cover
            flaatten_icon_to_png(image, exemplar_image, dark, nsview)

        flaatten_icon_to_png(image, output_path, dark, nsview)
        return image_diff(str(output_path), str(exemplar_image))

    return _test_image_diff


class TestIconImages:
    @pytest.mark.parametrize("dark", [True, False])
    @pytest.mark.parametrize("display", ["Text", "Dot"])
    @pytest.mark.parametrize("case, latency, loss", ping_thresholds)
    def test_status_icon(self, compare_image, case, latency, loss, display, dark):
        icon, view, _ = generate_status_icon(
            display,
            latency=latency,
            loss=loss,
            latency_thresholds=latency_thresholds,
            loss_thresholds=loss_thresholds,
        )
        assert (
            compare_image(
                icon,
                f"{display.lower()}-{case}-{'dark' if dark else 'light'}",
                dark,
                view,
            )
            < 0.01
        ), "Generated icon should match reference image"

    @pytest.mark.parametrize("dark", [True, False])
    def test_pause_icon(self, compare_image, dark):
        pause_icon = symbol_icon("pause.circle", "Paused")
        assert (
            compare_image(pause_icon, f"pause-{'dark' if dark else 'light'}", dark)
            < 0.01
        ), "Generated pause icon should match reference image"

    @pytest.mark.parametrize("dark", [True, False])
    def test_chart_icon(self, compare_image, dark):
        test_result_indexes = [0, 1, 2, 3, 5, 6, 8, 9, 10, 12, 13, 14]
        test_values = [ping_thresholds[i][-2:] for i in test_result_indexes]

        state = ""
        chart_icon = None
        chart_view = None

        for latency, loss in test_values:

            chart_icon, chart_view, state = generate_status_icon(
                style="Chart",
                latency=latency,
                loss=loss,
                latency_thresholds=latency_thresholds,
                loss_thresholds=loss_thresholds,
                last_state=state,
            )
        assert (
            compare_image(
                chart_icon, f"chart-{'dark' if dark else 'light'}", dark, chart_view
            )
            < 0.01
        ), "Generated chart icon should match reference image"

        _, _, new_state = generate_status_icon(
            style="Chart",
            latency=0.0,
            loss=0.0,
            latency_thresholds=latency_thresholds,
            loss_thresholds=loss_thresholds,
            last_state=state,
            force=True,
        )
        assert state == new_state, "State should not be updated when force is True"


class TestIconSameState:
    @pytest.mark.parametrize("style", ["Dot", "Text"])
    @pytest.mark.parametrize("case, latency, loss", ping_thresholds)
    def test_status_icon_same_state(self, style, case, latency, loss):
        icon1, _, state1 = generate_status_icon(
            style,
            latency=latency,
            loss=loss,
            last_state=None,
            latency_thresholds=latency_thresholds,
            loss_thresholds=loss_thresholds,
        )
        icon2, _, _ = generate_status_icon(
            style,
            latency=latency,
            loss=loss,
            last_state=state1,
            latency_thresholds=latency_thresholds,
            loss_thresholds=loss_thresholds,
        )
        assert icon1 is not None, "Icon should be generated on first call"
        assert icon2 is None, "Icon should not be regenerated if state is unchanged"
