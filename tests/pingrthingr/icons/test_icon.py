from AppKit import NSImage, NSBitmapImageRep, NSPNGFileType
from Foundation import NSURL
from pathlib import Path
import pytest
from pingrthingr.icons import symbol_icon, status_dot_icon

base_path = Path(__file__).parent


def nsimage_to_png(ns_image: NSImage, path: str) -> None:
    """Write an NSImage to a PNG file without requiring a display context.

    Uses TIFFRepresentation() to extract raw image data from the NSImage's
    internal representations, then converts to PNG via NSBitmapImageRep.
    This avoids lockFocus/CGImage calls that require an active screen context.

    Args:
        ns_image: The NSImage to convert.
        path: Destination file path for the PNG.
    """
    tiff_data = ns_image.TIFFRepresentation()
    assert tiff_data is not None, "NSImage has no TIFF representation"
    bitmap_rep = NSBitmapImageRep.imageRepWithData_(tiff_data)
    png_data = bitmap_rep.representationUsingType_properties_(NSPNGFileType, None)
    NSURL.fileURLWithPath_(path)
    png_data.writeToFile_atomically_(path, True)

@pytest.fixture
def compare_image(image_diff, tmp_path):
    def _test_image_diff(image: NSImage, test_name: str) -> float:
        exemplar_image = base_path / f"resources/example-{test_name}.png"
        output_path = tmp_path / f"compare-{test_name}.png"
        nsimage_to_png(image, str(output_path))
        return image_diff(str(output_path), str(exemplar_image))
    return _test_image_diff

def test_status_dot_icon(tmp_path, compare_image):
    dot_icon, _ = status_dot_icon(latency=100, loss=0.0)
    assert compare_image(dot_icon, "dot") < 0.01, "Generated icon should match reference image"

# def test_symbol_icon(tmp_path, image_diff):
#     output_path = tmp_path / "check.png"
#     exemplar_image = base_path / "resources/example-check.png"

#     ns_image = symbol_icon("checkmark.circle.fill", "circle-fill")
#     assert ns_image is not None, "symbol_icon should return a non-nil NSImage"
#     nsimage_to_png(ns_image, str(output_path))
#     assert output_path.exists(), "PNG file should be created"
#     assert image_diff(str(output_path), str(exemplar_image)) < 0.01, "Generated icon should match reference image"

