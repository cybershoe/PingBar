"""SF Symbol icon generation for PingrThingr.

Provides a helper for rendering named SF Symbols into fixed-size NSImage
objects suitable for the macOS menu bar.
"""

from AppKit import (
    NSColor,  # type: ignore[import]
    NSImage,  # type: ignore[import]
    NSMakeRect,  # type: ignore[import]
    NSSize,  # type: ignore[import]
    NSImageSymbolConfiguration,  # type: ignore[import]
)


def symbol_icon(
    symbol_name: str,
    accessibility_description: str,
    color: NSColor | None = None,
    small: bool = False,
) -> NSImage:
    """Create a template icon from an SF Symbol.

    This function creates a 20x20 pixel NSImage icon from the specified SF Symbol,
    suitable for use in macOS menu bars. The resulting image can optionally be
    colored and sized smaller for different display contexts.

    Args:
        symbol_name (str): The name of the SF Symbol (e.g., 'pause.circle').
        accessibility_description (str): Accessibility description for the icon.
        color (NSColor|None, optional): Color to apply to the symbol. If None,
                                       creates a template image for automatic theming.
                                       Defaults to None.
        small (bool, optional): If True, draws symbol in center 12x12 area for smaller
                               appearance. If False, fills entire 20x20 area.
                               Defaults to False.

    Returns:
        NSImage: A 20x20 pixel icon of the specified SF Symbol, optionally colored.
    """
    # Create SF Symbol image with configuration
    symbol_image = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
        symbol_name, accessibility_description
    )

    if color is not None:
        # Create a hierarchical color configuration and apply it to the symbol
        config = NSImageSymbolConfiguration.configurationWithHierarchicalColor_(color)
        symbol_image = symbol_image.imageWithSymbolConfiguration_(config)

    # Create a new 20x20 image
    size = NSSize(20, 20)
    image = NSImage.alloc().initWithSize_(size)

    image.lockFocus()

    # Draw the symbol image scaled to fit the 20x20 size
    if small:
        symbol_image.drawInRect_(NSMakeRect(4, 4, 12, 12))
    else:
        symbol_image.drawInRect_(NSMakeRect(0, 0, 20, 20))

    image.unlockFocus()
    if color is None:
        image.setTemplate_(True)

    return image
