import logging
logger = logging.getLogger(__name__)

from rumps import MenuItem
from typing import List, Callable

class SelectableMenu(MenuItem):
    def __init__(self, title="Select", options: List[str] = [], selected: str = None, cb: Callable = None, **kwargs):
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

    def _option_selected(self, sender):
        for item in self._menu_items:
            item.state = 0
        sender.state = 1
        if self._cb:
            self._cb(sender.title)

    def get_selected(self):
        for item in self._menu_items:
            if item.state == 1:
                return item.title
        return None
    
    def set_selected(self, option):
        for item in self._menu_items:
            item.state = 1 if item.title == option else 0