"""Rendering utilities for the icons package.

Provides low-level helpers for converting AppKit views into rasterised
NSImage objects.
"""

from AppKit import (
    NSView,  # type: ignore[import]
    NSImage,  # type: ignore[import]
)

def _nsview_to_nsimage(nsview: NSView) -> NSImage:
    """Render an NSView into an NSImage by capturing its display output.

    Creates a bitmap representation of the view at its current size and
    wraps it in an NSImage. The view does not need to be attached to a
    window for this to work.

    Args:
        nsview (NSView): The view to capture.

    Returns:
        NSImage: A rasterised image of the view's contents.
    """
    bounds = nsview.bounds()
    bitmap_rep = nsview.bitmapImageRepForCachingDisplayInRect_(bounds)
    nsview.cacheDisplayInRect_toBitmapImageRep_(bounds, bitmap_rep)
    image = NSImage.alloc().initWithSize_(bounds.size)
    image.addRepresentation_(bitmap_rep)
    return image