"""Settings and UI components module for PingrThingr application.

This module provides custom UI components and settings management
functionality for the PingrThingr menu bar application, including
selectable menu items and configuration widgets.

Classes:
    SelectableMenu: A custom MenuItem that displays options as sub-menu items.
"""

import logging

logger = logging.getLogger(__name__)

from rumps import MenuItem, Window, alert
from socket import inet_aton
from typing import List, Callable


class SelectableMenu(MenuItem):
    """A selectable menu component that displays options as checkable sub-menu items.

    This class extends MenuItem to create a menu with selectable options where
    only one option can be selected at a time. When an option is selected,
    a callback function is invoked with the selected option.
    """

    def __init__(
        self,
        title="Select",
        options: List[str] = None,
        selected: str = None,
        cb: Callable = None,
        **kwargs,
    ):
        """Initialize the SelectableMenu with options and callback.

        Args:
            title (str, optional): The main menu item title. Defaults to "Select".
            options (List[str], optional): List of option strings to display as sub-items.
                                         Defaults to None, which creates an empty list.
            selected (str, optional): Initially selected option. Must be in options list
                                    or None for no initial selection. Defaults to None.
            cb (Callable, optional): Callback function called with selected option string
                                   when selection changes. Defaults to None.
            **kwargs: Additional keyword arguments passed to parent MenuItem.
        """
        if options is None:
            options = []

        if selected is not None and selected not in options:
            raise ValueError("selected must be None or one of the provided options")
        self._base_title = title
        super(SelectableMenu, self).__init__(
            f"{title}: {selected}" if selected else title, **kwargs
        )
        self._menu_items = []
        cb_name = getattr(cb, "__name__", None)
        logger.debug(
            f"In SelectableMenu.__init__(): Initializing SelectableMenu with options: {options}, selected: {selected}, callback: {cb_name}"
        )
        for option in options:
            item = MenuItem(option, callback=self._option_selected)
            if option == selected:
                item.state = 1
            self._menu_items.append(item)
            logger.debug(f"Created menu item: {option} state: {item.state}")
        self.menu = self._menu_items
        for item in self._menu_items:
            self.add(item)
        self._cb = cb

    def _option_selected(self, sender) -> None:
        """Handle selection of a menu option.

        Called when a user clicks on one of the sub-menu items. Updates
        the selection state and calls the callback function if provided.

        Args:
            sender: The MenuItem that was selected.
        """
        for item in self._menu_items:
            item.state = 0
        sender.state = 1
        self.title = f"{self._base_title}: {sender.title}"
        if self._cb:
            self._cb(sender.title)

    def get_selected(self) -> str | None:
        """Get the currently selected option.

        Returns:
            str | None: The title of the currently selected menu item,
                       or None if no item is selected.
        """
        for item in self._menu_items:
            if item.state == 1:
                return item.title
        return None

    def set_selected(self, option: str) -> None:
        """Set the selected option programmatically.

        Args:
            option (str): The option to select. Must match one of the
                         options provided during initialization.
        """
        selected_item = None
        for item in self._menu_items:
            if item.title == option:
                selected_item = item
                break

        if selected_item is not None:
            self._option_selected(selected_item)
            return

        for item in self._menu_items:
            item.state = 0
        self.title = self._base_title


def update_ping_targets(targets: List[str]) -> List[str] | None:
    """Display preferences dialog for configuring ping targets.

    Shows a modal dialog window allowing the user to enter or modify
    the list of IP addresses to monitor. Validates all entered IP addresses
    and displays error messages for invalid entries.

    Args:
        targets (List[str]): Current list of target IP addresses.

    Returns:
        List[str] | None: Updated list of target IP addresses if user clicked Save,
                         or None if user clicked Cancel or closed the dialog.
    """
    while True:
        logger.debug(f"In update_ping_targets(): Current targets: {targets}")
        response = Window(
            title="Ping Targets",
            message="Enter target IP addresses (comma-separated):",
            default_text=",".join(targets),
            dimensions=(300, 24),
            cancel="Cancel",
            ok="Save",
        ).run()

        if response.clicked == 1:
            logger.debug(
                f"In update_ping_targets(): User entered targets: {response.text}"
            )
            new_targets = [t.strip() for t in response.text.split(",") if t.strip()]
            try:
                for target in new_targets:
                    inet_aton(target)
            except OSError:
                alert(f"Invalid IP address: {target}")
                logger.error(
                    f"In update_ping_targets(): Invalid IP address entered: {target}"
                )
            else:
                logger.debug(
                    f"In update_ping_targets(): Valid targets entered, returning: {new_targets}"
                )
                return new_targets
        else:
            logger.info("User cancelled preferences dialog")
            return None
