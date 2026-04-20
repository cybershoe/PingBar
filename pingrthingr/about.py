from .version import __VERSION__

from pathlib import Path
from re import sub as re_sub
from AppKit import (
    NSAlert,  # type: ignore[import]
    NSColor,  # type: ignore[import]
    NSForegroundColorAttributeName,  # type: ignore[import]
    NSMakeRect,  # type: ignore[import]
    NSMutableAttributedString,  # type: ignore[import]
    NSLinkAttributeName,  # type: ignore[import]
    NSScrollView,  # type: ignore[import]
    NSString,  # type: ignore[import]
    NSTextView,  # type: ignore[import]
    NSView,  # type: ignore[import]
)

license_file = base_path = Path(__file__).parent.parent / "LICENSE"


def show_about_window(_):  # pragma: no cover

    VIEW_WIDTH = 300
    SCROLL_HEIGHT = 180
    GAP = 10

    with open(license_file, "r") as f:
        license_text = f.read()

    license_text = re_sub("(?<![\r\n])(\r?\n|\n?\r)(?![\r\n])", " ", license_text)
    message_text = "Source code available on GitHub"

    attributed_string = NSMutableAttributedString.alloc().initWithString_(message_text)
    full_range = NSString.stringWithString_(message_text).rangeOfString_(message_text)
    attributed_string.addAttribute_value_range_(
        NSForegroundColorAttributeName,
        NSColor.labelColor(),
        full_range,
    )
    repo_link_range = NSString.stringWithString_(message_text).rangeOfString_("GitHub")
    attributed_string.addAttribute_value_range_(
        NSLinkAttributeName,
        "https://github.com/cybershoe/PingrThingr",
        repo_link_range,
    )

    text_view = NSTextView.alloc().initWithFrame_(NSMakeRect(0, 0, VIEW_WIDTH, 0))
    text_view.textStorage().setAttributedString_(attributed_string)
    text_view.setEditable_(False)
    text_view.setDrawsBackground_(False)
    text_view.textContainer().setContainerSize_((VIEW_WIDTH, float("inf")))
    text_view.textContainer().setWidthTracksTextView_(False)
    text_view.layoutManager().ensureLayoutForTextContainer_(text_view.textContainer())
    text_height = (
        text_view.layoutManager()
        .usedRectForTextContainer_(text_view.textContainer())
        .size.height
    )
    text_view.setFrame_(NSMakeRect(0, SCROLL_HEIGHT + GAP, VIEW_WIDTH, text_height))

    license_attributed = NSMutableAttributedString.alloc().initWithString_(license_text)
    license_full_range = NSString.stringWithString_(license_text).rangeOfString_(
        license_text
    )
    license_attributed.addAttribute_value_range_(
        NSForegroundColorAttributeName,
        NSColor.labelColor(),
        license_full_range,
    )

    license_text_view = NSTextView.alloc().initWithFrame_(NSMakeRect(0, 0, 300, 180))
    license_text_view.textStorage().setAttributedString_(license_attributed)
    license_text_view.setEditable_(False)
    license_text_view.setDrawsBackground_(False)

    license_scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(0, 0, 300, 180))
    license_scroll.setHasVerticalScroller_(True)
    license_scroll.setAutohidesScrollers_(True)
    license_scroll.setDocumentView_(license_text_view)

    container = NSView.alloc().initWithFrame_(
        NSMakeRect(0, 0, VIEW_WIDTH, SCROLL_HEIGHT + GAP + text_height)
    )
    container.addSubview_(text_view)
    container.addSubview_(license_scroll)

    alert = NSAlert.alloc().init()
    alert.setMessageText_(f"PingrThingr {__VERSION__}")
    alert.setAccessoryView_(container)
    alert.addButtonWithTitle_("OK")
    alert.runModal()
