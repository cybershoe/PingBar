from AppKit import (
    NSAppearance,  # type: ignore[import]
    NSAppearanceNameDarkAqua,  # type: ignore[import]
    NSAppearanceNameAqua,  # type: ignore[import]
    NSImage,  # type: ignore[import]
    NSBitmapImageRep,  # type: ignore[import]
    NSPNGFileType,  # type: ignore[import]
)
from Quartz import CGColorCreate, CGColorSpaceCreateDeviceRGB  # type: ignore[import]
from pathlib import Path
import pytest
from pingrthingr.settings import ThresholdModel
from pingrthingr.icons import (
    symbol_icon,
    # status_dot_icon,
    status_text_icon,
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


def nsimage_to_png(ns_image: NSImage, output_path):
    # 1. Get the TIFF representation of the NSImage
    tiff_data = ns_image.TIFFRepresentation()

    # 2. Create a bitmap image representation from that TIFF data
    bitmap_rep = NSBitmapImageRep.imageRepWithData_(tiff_data)

    # 3. Create the PNG data from the bitmap representation
    # NSPNGFileType is the constant for PNG (integer value 4)
    png_data = bitmap_rep.representationUsingType_properties_(NSPNGFileType, None)

    # 4. Write to disk
    png_data.writeToFile_atomically_(output_path, True)


@pytest.fixture
def compare_image(image_diff, tmp_path):
    def _test_image_diff(image: NSImage, test_name: str) -> float:
        exemplar_image = base_path / f"resources/example-{test_name}.png"
        output_path = tmp_path / f"compare-{test_name}.png"
        if not Path(exemplar_image).is_file():  # pragma: no cover
            nsimage_to_png(image, str(exemplar_image))

        nsimage_to_png(image, str(output_path))
        return image_diff(str(output_path), str(exemplar_image))

    return _test_image_diff


class TestIconImages:
    @pytest.mark.parametrize("dark", [True, False])
    @pytest.mark.parametrize("display", ["Text", "Dot"])
    @pytest.mark.parametrize("case, latency, loss", ping_thresholds)
    def test_status_icon(self, compare_image, case, latency, loss, display, dark):
        # Skip visual testing for headless environments
        icon, _ = generate_status_icon(
            display,
            latency=latency,
            loss=loss,
            latency_thresholds=latency_thresholds,
            loss_thresholds=loss_thresholds,
            appearance=(
                NSAppearance.appearanceNamed_(NSAppearanceNameDarkAqua)
                if dark
                else NSAppearance.appearanceNamed_(NSAppearanceNameAqua)
            ),
        )
        assert (
            compare_image(
                icon, f"{display.lower()}-{case}-{'dark' if dark else 'light'}"
            )
            < 0.01
        ), "Generated icon should match reference image"

    def test_pause_icon(self, compare_image):
        pause_icon = symbol_icon("pause.circle", "Paused")
        assert (
            compare_image(pause_icon, "pause") < 0.01
        ), "Generated pause icon should match reference image"


class TestIconSameState:
    @pytest.mark.parametrize("style", ["Dot", "Text"])
    @pytest.mark.parametrize("case, latency, loss", ping_thresholds)
    def test_status_icon_same_state(self, style, case, latency, loss):
        icon1, state1 = generate_status_icon(
            style,
            latency=latency,
            loss=loss,
            last_state=None,
            latency_thresholds=latency_thresholds,
            loss_thresholds=loss_thresholds,
            appearance=NSAppearance.appearanceNamed_(NSAppearanceNameAqua)
        )
        icon2, _ = generate_status_icon(
            style,
            latency=latency,
            loss=loss,
            last_state=state1,
            latency_thresholds=latency_thresholds,
            loss_thresholds=loss_thresholds,
            appearance=NSAppearance.appearanceNamed_(NSAppearanceNameAqua)
        )
        assert icon1 is not None, "Icon should be generated on first call"
        assert icon2 is None, "Icon should not be regenerated if state is unchanged"
