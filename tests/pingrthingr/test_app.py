import pytest

from pingrthingr import PingrThingrApp
from pathlib import Path
from time import sleep


class TestPingrThingrAppInitialization:

    # @pytest.fixture(autouse=True)
    # def setup(self, tmp_path, mocker):
    #     # Mock the Pinger to avoid actual network activity during tests
    #     self.mock_pinger = mocker.MagicMock()
    #     mocker.patch("pingrthingr.app.Pinger", return_value=self.mock_pinger)
    #     # Mock application_support to use a temporary directory for settings
    #     mocker.patch("pingrthingr.app.application_support", return_value=str(tmp_path))

    @pytest.fixture(autouse=True)
    def mocked_app(self, mocker, tmp_path):
        # Create an instance of the app for testing
        mock_pinger = mocker.MagicMock()
        mocker.patch("pingrthingr.app.Pinger", return_value=mock_pinger)
        mocker.patch("pingrthingr.app.application_support", return_value=str(tmp_path))
        app = PingrThingrApp("testapp")
        mock_nsapp = mocker.MagicMock()
        mocker.patch.object(app, "_nsapp", mock_nsapp, create=True)

        yield app, mock_pinger, mock_nsapp

    def test_initialization(self, mocked_app, tmp_path):
        app, _, _ = mocked_app
        assert app._settings is not None, "SettingsManager should be initialized"
        assert app.pinger is not None, "Pinger should be initialized"
        assert app.menu is not None, "Menu should be initialized"
        assert app.statistics_menu is not None, "Statistics menu item should be initialized"
        assert app.pause_menu is not None, "Pause menu item should be initialized"
        assert app.display_menu is not None, "Display menu should be initialized"
        assert app._icon_nsimage is not None, "Icon NSImage should be initialized"  
        assert Path(app._settings_path) == tmp_path / "settings.json", "Settings file path should be correctly set"

    def test_ping_response_updates(self, mocked_app):
        app, _, mocked_nsapp = mocked_app
        # Simulate a ping response and check if statistics are updated
        app.refresh_status_(latency=100, loss=0)
        assert app.latency == 100, "Latency should be updated to 100"
        assert app.loss == 0, "Loss should be updated to 0"
        assert app.statistics_menu.title != "waiting...", "Statistics menu title should be updated" 
        assert mocked_nsapp.setStatusBarIcon.called, "NSApp.setMenuBarIcon should be called to update the icon"

    def test_pause(self, mocked_app, tmp_path):
        app, mock_pinger, mock_nsapp = mocked_app
        app._settings.set("paused",True)
        mock_pinger.run.assert_called_with(False)
        assert app.pause_menu.state == True, "Pause menu state should be set to True when paused"
        assert app.latency is None and app.loss is None, "Latency and loss should be reset to None when paused"
        assert mock_nsapp.setStatusBarIcon.called, "NSApp.setMenuBarIcon should be called to update the icon when paused"
        settings_file = tmp_path / "settings.json"
        assert settings_file.is_file(), "Settings file should be created"
        settings_data = settings_file.read_text()
        assert '"paused": true' in settings_data, "Settings file should reflect paused state"