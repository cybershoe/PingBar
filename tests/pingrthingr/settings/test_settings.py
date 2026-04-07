import pytest
from typing import Callable, Tuple
from unittest.mock import Mock
from rumps import MenuItem
from pingrthingr.settings.settings import SelectableMenu

class TestSelectableMenu:

    @pytest.fixture
    def mock_selectable_menu(self, mocker):
        mock_cb = Mock()
        def _mock_selectable_menu(
                title="Test Menu",
                options: list[str] = ["Option 1", "Option 2", "Option 3"],
                selected: str = "Option 1",
                cb: Callable = mock_cb,

        ):
            mock_menu_item = mocker.patch("rumps.MenuItem", autospec=True)
            return SelectableMenu(title=title, options=options, selected=selected, cb=cb), cb
        
        return _mock_selectable_menu
    
    def test_initialization(self, mock_selectable_menu):
        menu, mock_cb = mock_selectable_menu()
        assert menu.title == "Test Menu: Option 1", "Menu title should include selected option"
        assert len(menu._menu_items) == 3, "Menu should have 3 options"
        for item in menu._menu_items:
            assert isinstance(item, MenuItem), "Sub-menu items should be MenuItem instances"
            assert item.callback == menu._option_selected, "Sub-menu items should have correct callback"
            assert item.state == (1 if item.title == "Option 1" else 0), "Selected item should have state 1, others should have state 0"
        mock_cb.assert_not_called()  # Callback should not be called during initialization  

    def test_option_selection(self, mock_selectable_menu):
        menu, mock_cb = mock_selectable_menu()
        assert menu.get_selected() == "Option 1", "Initially selected option should be 'Option 1'"
        # Simulate selecting "Option 2"
        option_2_item = next(item for item in menu._menu_items if item.title == "Option 2")
        menu.set_selected("Option 2")
        assert option_2_item.state == 1, "Selected item should have state 1"
        assert menu.title == "Test Menu: Option 2", "Menu title should update to selected option"
        for item in menu._menu_items:
            if item.title != "Option 2":
                assert item.state == 0, "Non-selected items should have state 0"
        mock_cb.assert_called_once_with("Option 2")  # Callback should be called with selected option

    def test_no_options(self, mock_selectable_menu):
        menu, mock_cb = mock_selectable_menu(options=[], selected=None)
        assert len(menu._menu_items) == 0, "Menu should have no options"
        assert menu.get_selected() is None, "No option should be selected"
        menu.set_selected("Option 1")  # Should not raise an error even though there are no options
        mock_cb.assert_not_called()  # Callback should not be called when setting selection with no options

    def test_set_with_invalid_selected_option(self, mock_selectable_menu):
        pytest.raises(ValueError, mock_selectable_menu, options=["Option A", "Option B"], selected="Invalid Option")

    def test_set_selected_with_invalid_option(self, mock_selectable_menu):
        menu, mock_cb = mock_selectable_menu()
        menu.set_selected("Invalid Option")  # Should not raise an error, but should not change selection
        assert menu.get_selected() is None, "Invalid selected option should result in no selection"
        assert menu.title == "Test Menu", "Menu title should not include selected option if selection is invalid"