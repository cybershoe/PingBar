import pytest

from pingrthingr import PingrThingrApp
from pathlib import Path


class TestPingrThingrAppInitialization:

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path, mocker):

        # Mock the Pinger to avoid actual network activity during tests
        self.mock_pinger = mocker.MagicMock()
        mocker.patch("pingrthingr.app.Pinger", return_value=self.mock_pinger)

        # Mock application_support to use a temporary directory for settings
        mocker.patch("pingrthingr.app.application_support", return_value=str(tmp_path))

    def test_initialization(self, tmp_path):
        app = PingrThingrApp("testapp")
        assert app._settings is not None, "SettingsManager should be initialized"
        assert app.pinger is not None, "Pinger should be initialized"
        assert app.menu is not None, "Menu should be initialized"
        assert app.statistics_menu is not None, "Statistics menu item should be initialized"
        assert app.pause_menu is not None, "Pause menu item should be initialized"
        assert app.display_menu is not None, "Display menu should be initialized"
        assert app._icon_nsimage is not None, "Icon NSImage should be initialized"  
        assert Path(app._settings_path) == tmp_path / "settings.json", "Settings file path should be correctly set"
