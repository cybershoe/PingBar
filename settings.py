"""Settings and UI components module for PingBar application.

This module provides custom UI components and settings management
functionality for the PingBar menu bar application, including
selectable menu items and configuration widgets.

Classes:
    SelectableMenu: A custom MenuItem that displays options as sub-menu items.
"""
import logging
logger = logging.getLogger(__name__)

from rumps import MenuItem
from typing import List, Callable

class SelectableMenu(MenuItem):
    """A selectable menu component that displays options as checkable sub-menu items.
    
    This class extends MenuItem to create a menu with selectable options where
    only one option can be selected at a time. When an option is selected,
    a callback function is invoked with the selected option.
    """
    
    def __init__(self, title="Select", options: List[str] = [], selected: str = None, cb: Callable = None, **kwargs):
        """Initialize the SelectableMenu with options and callback.
        
        Args:
            title (str, optional): The main menu item title. Defaults to "Select".
            options (List[str], optional): List of option strings to display as sub-items. 
                                         Defaults to [].
            selected (str, optional): Initially selected option. Must be in options list
                                    or None for no initial selection. Defaults to None.
            cb (Callable, optional): Callback function called with selected option string
                                   when selection changes. Defaults to None.
            **kwargs: Additional keyword arguments passed to parent MenuItem.
        """
        super(SelectableMenu, self).__init__(title, **kwargs)
        self._menu_items = []
        logger.debug(f"In SelectableMenu.__init__(): Initializing SelectableMenu with options: {options}, selected: {selected}, callback: {cb.__name__}")
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
        for item in self._menu_items:
            item.state = 1 if item.title == option else 0