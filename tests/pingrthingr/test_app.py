import pytest

from pingrthingr import PingrThingrApp
from pingrthingr.icons import generate_status_icon
from pingrthingr.settings.models import ThresholdModel
from pathlib import Path
from json import load as json_load


@pytest.fixture(autouse=True)
def mocked_app(mocker, tmp_path):
    # Create an instance of the app for testing
    mock_pinger = mocker.MagicMock()
    mocker.patch("pingrthingr.app.Pinger", return_value=mock_pinger)
    mocker.patch("pingrthingr.app.application_support", return_value=str(tmp_path))
    app = PingrThingrApp("testapp")
    mock_nsapp = mocker.MagicMock()
    mocker.patch.object(app, "_nsapp", mock_nsapp, create=True)

    yield app, mock_pinger, mock_nsapp


# @pytest.fixture(autouse=True)
# def mocked_ns_block_operation(mocker):
#     mock_ns_block_operation = mocker.MagicMock()
#     mock_ns_operation_queue = mocker.MagicMock()
#     mocker.patch("pingrthingr.app.NSBlockOperation", mock_ns_block_operation)
#     mocker.patch("pingrthingr.app.NSOperationQueue", mock_ns_operation_queue)
#     yield mock_ns_block_operation

@pytest.fixture(autouse=True)
def mocked_ns_timer(mocker):
    mock_ns_timer = mocker.MagicMock()
    mock_ns_runloop = mocker.MagicMock()
    mocker.patch("pingrthingr.app.NSTimer", mock_ns_timer)
    mocker.patch("pingrthingr.app.NSRunLoop", mock_ns_runloop)
    yield mock_ns_timer, mock_ns_runloop


class TestPingrThingrAppInitialization:
    def test_initialization(self, mocked_app, tmp_path):
        app, _, _ = mocked_app
        assert app._settings is not None, "SettingsManager should be initialized"
        assert app.pinger is not None, "Pinger should be initialized"
        assert app.menu is not None, "Menu should be initialized"
        assert (
            app.statistics_menu is not None
        ), "Statistics menu item should be initialized"
        assert app.pause_menu is not None, "Pause menu item should be initialized"
        assert app.display_menu is not None, "Display menu should be initialized"
        assert app._icon_nsimage is not None, "Icon NSImage should be initialized"
        assert (
            Path(app._settings_path) == tmp_path / "settings.json"
        ), "Settings file path should be correctly set"


class TestPingUpdates:
    def test_ping_response_updates(self, mocked_app, mocked_ns_timer, mocker):
        app, _, mocked_nsapp = mocked_app

        NSTimer, NSRunloop = mocked_ns_timer
        NSTimer.timerWithTimeInterval_target_selector_userInfo_repeats_.return_value = mocker.MagicMock() 
        # Simulate a ping response and check if statistics are updated
        app.update_statistics(latency=100, loss=0)
        assert (
            NSTimer.timerWithTimeInterval_target_selector_userInfo_repeats_.call_count == 1
        ), "NSBlockOperation should be created to update statistics"

        print(NSTimer.timerWithTimeInterval_target_selector_userInfo_repeats_.call_args)
        args = NSTimer.timerWithTimeInterval_target_selector_userInfo_repeats_.call_args[0]
        
        # Call the block to execute the statistics update
        NSTimer.userInfo.returns = args[3]  # Simulate userInfo being passed to the selector
        getattr(args[1], args[2].replace(":", "_"))(NSTimer)
        # print(args[3])  # time interval
        return

        assert app.latency == 100, "Latency should be updated to 100"
        assert app.loss == 0, "Loss should be updated to 0"
        assert (
            app.statistics_menu.title != "waiting..."
        ), "Statistics menu title should be updated"
        assert (
            mocked_nsapp.setStatusBarIcon.called
        ), "NSApp.setMenuBarIcon should be called to update the icon"

    def test_no_update_when_same(self, mocked_app, mocked_ns_block_operation):
        app, _, mocked_nsapp = mocked_app
        mocked_nsapp.setStatusBarIcon.reset_mock()  # Reset mock call count
        app.update_statistics(latency=100, loss=0)
        assert (
            mocked_ns_block_operation.blockOperationWithBlock_.call_count == 1
        ), "NSBlockOperation should be created to update statistics"
        mocked_ns_block_operation.blockOperationWithBlock_.call_args[0][
            0
        ]()  # Call the block to execute the statistics update
        assert (
            mocked_nsapp.setStatusBarIcon.call_count == 1
        ), "NSApp.setMenuBarIcon should be called to update the icon"

        app.update_statistics(latency=100, loss=0)
        assert (
            mocked_ns_block_operation.blockOperationWithBlock_.call_count == 2
        ), "NSBlockOperation should be created to update statistics"
        mocked_ns_block_operation.blockOperationWithBlock_.call_args[0][
            0
        ]()  # Call the block to execute the statistics update
        assert (
            mocked_nsapp.setStatusBarIcon.call_count == 1
        ), "NSApp.setMenuBarIcon should not have been called again"


class TestSettingsChanges:
    def test_pause(self, mocked_app, tmp_path, mocker):
        app, mock_pinger, mock_nsapp = mocked_app
        mock_sender = mocker.MagicMock(state=False)
        app.pause_toggle(mock_sender)
        mock_pinger.run.assert_called_with(False)
        assert (
            app.pause_menu.state == True
        ), "Pause menu state should be set to True when paused"
        assert (
            app.latency is None and app.loss is None
        ), "Latency and loss should be reset to None when paused"
        assert (
            mock_nsapp.setStatusBarIcon.called
        ), "NSApp.setMenuBarIcon should be called to update the icon when paused"
        settings_file = tmp_path / "settings.json"
        assert settings_file.is_file(), "Settings file should be created"
        settings_data = json_load(open(settings_file))
        assert (
            settings_data.get("paused") is True
        ), "Settings file should reflect paused state"

    def test_display_mode_change(self, mocked_app, tmp_path):
        app, _, mock_nsapp = mocked_app
        app._settings.set("display_mode", "Text")
        assert (
            mock_nsapp.setStatusBarIcon.called
        ), "NSApp.setMenuBarIcon should be called to update the icon when display mode changes"
        settings_file = tmp_path / "settings.json"
        assert settings_file.is_file(), "Settings file should be created"
        settings_data = json_load(open(settings_file))
        assert (
            settings_data.get("display_mode") == "Text"
        ), "Settings file should reflect display mode change"
        app._settings.set("display_mode", "Dot")
        assert (
            mock_nsapp.setStatusBarIcon.called
        ), "NSApp.setMenuBarIcon should be called to update the icon when display mode changes"

    def test_ping_target_window(self, mocked_app, mocker, tmp_path):
        app, _, _ = mocked_app
        new_targets = ["3.4.5.6", "7.8.9.10"]
        mocker.patch("pingrthingr.app.ping_target_window", return_value=new_targets)
        app.ping_targets(None)
        settings_file = tmp_path / "settings.json"
        settings_data = json_load(open(settings_file))
        assert (
            settings_data.get("targets") == new_targets
        ), "Settings file should reflect updated ping targets"

    def test_cancelled_ping_targets(self, mocked_app, mocker, tmp_path):
        app, _, _ = mocked_app
        mocker.patch("pingrthingr.app.ping_target_window", return_value=None)
        settings_file = tmp_path / "settings.json"
        pre_app_targets = app._settings.get("targets")
        app.ping_targets(None)
        assert (
            app._settings.get("targets") == pre_app_targets
        ), "Settings should not be updated when update is cancelled"
        assert (
            not settings_file.is_file()
        ), "Settings file should not be created when update is cancelled"


class TestIconRendering:
    def test_nsview_clearance(self, mocked_app, mocker):

        app, _, mock_nsapp = mocked_app

        icon, _ = generate_status_icon(
            "Text",
            latency=100,
            loss=0,
            latency_thresholds=ThresholdModel(warn=80, alert=500, critical=1000),
            loss_thresholds=ThresholdModel(warn=0.0, alert=0.01, critical=0.25),
        )

        mock_nsapp.nsstatusitem.button().subviews.return_value = [
            mocker.Mock()
        ]  # Simulate existing subviews
        app._draw_icon(icon)
        assert (
            mock_nsapp.nsstatusitem.button()
            .subviews()[0]
            .removeFromSuperview.call_count
            == 1
        ), "Existing subviews should be removed when drawing a new icon"
