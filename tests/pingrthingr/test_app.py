import pytest

from pingrthingr import PingrThingrApp
from pathlib import Path
from json import load as json_load
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

    def test_ping_response_updates(self, mocked_app, mocker):
        app, _, mocked_nsapp = mocked_app
        mock_ns_block_operation = mocker.MagicMock()
        mock_ns_operation_queue = mocker.MagicMock()
        mocker.patch("pingrthingr.app.NSBlockOperation", mock_ns_block_operation)
        mocker.patch("pingrthingr.app.NSOperationQueue", mock_ns_operation_queue)

        # Simulate a ping response and check if statistics are updated
        app.update_statistics(latency=100, loss=0)
        assert mock_ns_block_operation.blockOperationWithBlock_.call_count == 1, "NSBlockOperation should be created to update statistics"
        mock_ns_block_operation.blockOperationWithBlock_.call_args[0][0]()  # Call the block to execute the statistics update
        assert app.latency == 100, "Latency should be updated to 100"
        assert app.loss == 0, "Loss should be updated to 0"
        assert app.statistics_menu.title != "waiting...", "Statistics menu title should be updated" 
        assert mocked_nsapp.setStatusBarIcon.called, "NSApp.setMenuBarIcon should be called to update the icon"

    def test_pause(self, mocked_app, tmp_path, mocker):
        app, mock_pinger, mock_nsapp = mocked_app
        mock_sender = mocker.MagicMock(state=False)
        app.pause_toggle(mock_sender)
        mock_pinger.run.assert_called_with(False)
        assert app.pause_menu.state == True, "Pause menu state should be set to True when paused"
        assert app.latency is None and app.loss is None, "Latency and loss should be reset to None when paused"
        assert mock_nsapp.setStatusBarIcon.called, "NSApp.setMenuBarIcon should be called to update the icon when paused"
        settings_file = tmp_path / "settings.json"
        assert settings_file.is_file(), "Settings file should be created"
        settings_data = json_load(open(settings_file))
        assert settings_data.get("paused") is True, "Settings file should reflect paused state"

    def test_display_mode_change(self, mocked_app, tmp_path):
        app, _, mock_nsapp = mocked_app
        app._settings.set("display_mode", "Text")
        assert mock_nsapp.setStatusBarIcon.called, "NSApp.setMenuBarIcon should be called to update the icon when display mode changes"
        settings_file = tmp_path / "settings.json"
        assert settings_file.is_file(), "Settings file should be created"
        settings_data = json_load(open(settings_file))
        assert settings_data.get("display_mode") == "Text", "Settings file should reflect display mode change"
        app._settings.set("display_mode", "Dot")
        assert mock_nsapp.setStatusBarIcon.called, "NSApp.setMenuBarIcon should be called to update the icon when display mode changes"

    def test_update_ping_targets(self, mocked_app, mocker, tmp_path):
        app, _, _ = mocked_app
        new_targets = ["3.4.5.6", "7.8.9.10"]
        mocker.patch('pingrthingr.settings.update_ping_targets', return_value=new_targets)
        app._settings.set("targets", new_targets)
        settings_file = tmp_path / "settings.json"
        settings_data = json_load(open(settings_file))
        assert settings_data.get("targets") == new_targets, "Settings file should reflect updated ping targets"

    def test_cancelled_ping_targets(self, mocked_app, mocker, tmp_path):
        app, _, _ = mocked_app
        mocker.patch('pingrthingr.settings.update_ping_targets', return_value=None)
        settings_file = tmp_path / "settings.json"
        assert app._settings.get("targets") == [], "Settings should not be updated when update is cancelled"
        assert not settings_file.is_file(), "Settings file should not be created when update is cancelled"