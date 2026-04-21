"""Rendering utilities for the icons package.

Provides low-level helpers for converting AppKit views into rasterised
NSImage objects and for compositing multiple NSImages into an NSView.
"""

from AppKit import (
    NSMakeRect,  # type: ignore[import]
    NSView,  # type: ignore[import]
    NSImage,  # type: ignore[import]
    NSImageView,  # type: ignore[import]
    NSImageScaleNone,  # type: ignore[import]
)


def combine_template_and_color_images(
    template_image: NSImage, color_image: NSImage
) -> NSView:
    """Layer a coloured NSImage on top of a template NSImage inside an NSView.

    Both images must have the same dimensions.  The template image is placed
    in the bottom layer so that macOS can tint it according to the current
    menu-bar appearance (light / dark).  The colour image is placed in the
    top layer and drawn with its explicit colours preserved.

    The returned NSView is not attached to any window; it can be rasterised
    with :func:`_nsview_to_nsimage` or assigned directly to a status-bar item
    that accepts an NSView.

    Args:
        template_image (NSImage): An ``isTemplate``-flagged NSImage whose
            shape will be tinted by macOS to match the menu-bar appearance.
        color_image (NSImage): An NSImage whose explicit colours should be
            composited on top of the template layer without modification.

    Returns:
        NSView: A view whose bounds match the size of the supplied images and
        which contains both image layers stacked in drawing order.
    """
    size = template_image.size()
    frame = NSMakeRect(0, 0, size.width, size.height)

    container = NSView.alloc().initWithFrame_(frame)

    template_view = NSImageView.alloc().initWithFrame_(frame)
    template_view.setImage_(template_image)
    template_view.setImageScaling_(NSImageScaleNone)

    color_view = NSImageView.alloc().initWithFrame_(frame)
    color_view.setImage_(color_image)
    color_view.setImageScaling_(NSImageScaleNone)

    container.addSubview_(template_view)
    container.addSubview_(color_view)

    return container


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
