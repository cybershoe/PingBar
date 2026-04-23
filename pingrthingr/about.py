"""About window for PingrThingr.

Displays application version, copyright, a clickable GitHub link, and a
scrollable MIT licence text in a non-blocking NSAlert panel.
"""
import logging

logger = logging.getLogger(__name__)

from .version import __VERSION__

from re import sub as re_sub
from subprocess import run as subprocess_run
from AppKit import (
    NSAlert,  # type: ignore[import]
    NSAlertSecondButtonReturn,  # type: ignore[import]
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

LICENSE_TEXT = """
MIT License

Copyright (c) 2026 Adam Schumacher

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

def show_about_window(sender, settings_path: str | None = None):  # pragma: no cover
    """Display the About window.

    Builds an NSAlert containing a brief copyright and GitHub link at the top
    and a scrollable MIT licence text view below, then runs it as a modal.
    The application is activated before running the alert so it appears
    correctly even when built as an LSUIElement bundle.

    Args:
        _: Unused sender argument required by the rumps menu callback protocol.
    """

    VIEW_WIDTH = 300
    SCROLL_HEIGHT = 180
    GAP = 10

    license_text = re_sub("(?<![\r\n])(\r?\n|\n?\r)(?![\r\n])", " ", LICENSE_TEXT)
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
    if settings_path is not None:
        alert.addButtonWithTitle_("Open settings.json...")
    response = alert.runModal()
    if response == NSAlertSecondButtonReturn and settings_path is not None:
        logger.debug(settings_path)
        subprocess_run(["open", "-a", "TextEdit", settings_path])
