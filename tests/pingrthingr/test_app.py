"""Integration tests for PingrThingrApp.

Tests cover application initialisation, cross-thread scheduling via
MainThreadDispatcher, ping result handling, settings persistence, update
check logic, and icon rendering.
"""

import pytest
from pathlib import Path
from json import load as json_load, dump as json_dump

from pytest_mock import mocker

from pingrthingr import PingrThingrApp
from pingrthingr.icons import generate_status_icon
from pingrthingr.settings import ThresholdModel
from AppKit import NSAppearance, NSAppearanceNameAqua  # type: ignore

base_path = Path(__file__).parent


@pytest.fixture(autouse=True)
def mocked_app(mocker, tmp_path):
    """Autouse fixture that provides a factory for a fully mocked PingrThingrApp.

    Patches ``Pinger`` and ``application_support`` so no real network activity
    or filesystem side-effects occur. Optionally writes a settings file before
    constructing the app. Also wires up a synchronous ``MainThreadDispatcher``
    so that ``_run_in_main_thread`` calls execute inline during tests.

    Args:
        mocker: pytest-mock mocker fixture.
        tmp_path: pytest temporary directory used as the app support folder.

    Yields:
        Callable[[dict | None], Tuple[PingrThingrApp, MagicMock, MagicMock]]:
        A factory that accepts an optional settings dict and returns
        (app, mock_pinger, mock_nsapp).
    """

    def _mocked_app(settings: dict | None = None):
        # Create an instance of the app for testing
        mock_pinger = mocker.MagicMock()
        mocker.patch("pingrthingr.app.Pinger", return_value=mock_pinger)
        mocker.patch("pingrthingr.app.application_support", return_value=str(tmp_path))
        if settings is not None:
            with open(base_path / "settings/resources/default_settings.json") as f:
                default_settings = json_load(f)
            default_settings.update(settings)
            settings_file = tmp_path / "settings.json"
            with open(settings_file, "w") as f:
                json_dump(default_settings, f)
        app = PingrThingrApp("testapp")
        mock_nsapp = mocker.MagicMock()

        mocker.patch.object(app, "_nsapp", mock_nsapp, create=True)
        mock_button = mocker.MagicMock()
        mock_button.effectiveAppearance.return_value = NSAppearance.appearanceNamed_(
            NSAppearanceNameAqua
        )
        mock_nsapp.nsstatusitem.button.return_value = mock_button

        app._dispatcher = app.MainThreadDispatcher.alloc().init()
        app._dispatcher._app = app

        def mock_performSelectorOnMainThread_withObject_waitUntilDone_(
            target, userdata, wait_until_done
        ):
            app._dispatcher.dispatchSelector_(userdata)

        app._dispatcher.performSelectorOnMainThread_withObject_waitUntilDone_ = (
            mock_performSelectorOnMainThread_withObject_waitUntilDone_
        )

        return app, mock_pinger, mock_nsapp

    yield _mocked_app


class TestCrossThreadScheduling:
    def test_run_in_main_thread(self, mocked_app, mocker):
        app, _, _ = mocked_app()

        mock_test_function = mocker.MagicMock(__name__="mock_test_function")
        app.test_function = mock_test_function

        # Call _run_in_main_thread with our test function
        app._run_in_main_thread("test_function", "positional", key1="key_value1")

        assert mock_test_function.called
        assert mock_test_function.call_args == (
            ("positional",),
            {"key1": "key_value1"},
        ), "Function should be called with correct arguments"

    def test_bad_pickle(self, mocked_app, mocker, caplog):
        app, _, _ = mocked_app()
        userdata = b"not a pickle"
        with caplog.at_level("ERROR"):
            app._dispatcher.dispatchSelector_(userdata)
            assert (
                "Error unpickling userdata from selector" in caplog.text
            ), "Should log an error when unpickling fails"

    def test_no_function(self, mocked_app, mocker):
        app, _, _ = mocked_app()
        import pickle

        userdata = pickle.dumps(
            {"func": "non_existent_function", "args": (), "kwargs": {}}
        )
        with pytest.raises(KeyError):
            app._dispatcher.dispatchSelector_(userdata)


class TestPingrThingrAppInitialization:
    def test_initialization(self, mocked_app, tmp_path):
        app, _, _ = mocked_app()
        assert app._settings is not None, "SettingsManager should be initialized"
        assert app._pinger is not None, "Pinger should be initialized"
        assert app.menu is not None, "Menu should be initialized"
        assert (
            app._statistics_menu is not None
        ), "Statistics menu item should be initialized"
        assert app._pause_menu is not None, "Pause menu item should be initialized"
        assert app._display_menu is not None, "Display menu should be initialized"
        assert app._icon_nsimage is not None, "Icon NSImage should be initialized"
        assert (
            Path(app._settings_path) == tmp_path / "settings.json"
        ), "Settings file path should be correctly set"


class TestPingUpdates:
    def test_ping_response_updates(self, mocked_app):
        app, _, mocked_nsapp = mocked_app()

        # Simulate a ping response and check if statistics are updated
        app.update_statistics_cb(latency=100, loss=0)
        assert app.latency == 100, "Latency should be updated to 100"
        assert app.loss == 0, "Loss should be updated to 0"
        assert (
            app._statistics_menu.title != "waiting..."
        ), "Statistics menu title should be updated"
        assert (
            mocked_nsapp.setStatusBarIcon.called
        ), "NSApp.setMenuBarIcon should be called to update the icon"

    def test_ping_response_no_update_when_same(self, mocked_app):
        app, _, mocked_nsapp = mocked_app()
        mocked_nsapp.setStatusBarIcon.reset_mock()  # Reset mock call count
        app.update_statistics_cb(latency=100, loss=0)
        assert (
            mocked_nsapp.setStatusBarIcon.call_count == 1
        ), "NSApp.setMenuBarIcon should be called to update the icon"

        app.update_statistics_cb(latency=100, loss=0)
        assert (
            mocked_nsapp.setStatusBarIcon.call_count == 1
        ), "NSApp.setMenuBarIcon should not have been called again"


class TestSettingsChanges:
    def test_pause(self, mocked_app, tmp_path, mocker):
        app, mock_pinger, mock_nsapp = mocked_app()
        mock_sender = mocker.MagicMock(state=False)
        app._pause_menu_cb(mock_sender)
        mock_pinger.run.assert_called_with(False)
        assert (
            app._pause_menu.state == True
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
        app, _, mock_nsapp = mocked_app()
        app._display_menu.set_selected("Text")
        assert (
            mock_nsapp.setStatusBarIcon.called
        ), "NSApp.setMenuBarIcon should be called to update the icon when display mode changes"
        settings_file = tmp_path / "settings.json"
        assert settings_file.is_file(), "Settings file should be created"
        settings_data = json_load(open(settings_file))
        assert (
            settings_data.get("display_mode") == "Text"
        ), "Settings file should reflect display mode change"
        app._display_menu.set_selected("Dot")
        assert (
            mock_nsapp.setStatusBarIcon.called
        ), "NSApp.setMenuBarIcon should be called to update the icon when display mode changes"

    def test_ping_target_window(self, mocked_app, mocker, tmp_path):
        app, _, _ = mocked_app()
        new_targets = ["3.4.5.6", "7.8.9.10"]
        mocker.patch("pingrthingr.app.ping_target_window", return_value=new_targets)
        app._ping_targets_menu_cb(None)
        settings_file = tmp_path / "settings.json"
        settings_data = json_load(open(settings_file))
        assert (
            settings_data.get("targets") == new_targets
        ), "Settings file should reflect updated ping targets"

    def test_cancelled_ping_targets(self, mocked_app, mocker, tmp_path):
        app, _, _ = mocked_app()
        mocker.patch("pingrthingr.app.ping_target_window", return_value=None)
        settings_file = tmp_path / "settings.json"
        pre_app_targets = app._settings.get("targets")
        app._ping_targets_menu_cb(None)
        assert (
            app._settings.get("targets") == pre_app_targets
        ), "Settings should not be updated when update is cancelled"
        assert (
            not settings_file.is_file()
        ), "Settings file should not be created when update is cancelled"


class TestCheckForUpdates:
    def test_check_for_updates(self, mocked_app, mocker):
        app, _, _ = mocked_app()
        mocked_update = mocker.MagicMock()
        mocker.patch("pingrthingr.app.run_update_check", mocked_update)
        mocked_dialog = mocker.MagicMock()
        mocker.patch("pingrthingr.app.update_dialog", mocked_dialog)
        mocker.patch("pingrthingr.app.__VERSION__", "v0.2.0")

        # Check update invocation via menu
        app._check_for_updates_menu_cb(app._check_for_updates_menu)
        mocked_update.assert_called_once_with(
            "v0.2.0", app.check_for_updates_return, False
        )
        assert app._check_for_updates_menu.callback == None
        assert app._check_for_updates_menu.title == "Checking for updates..."

        # Check callback handling
        app.check_for_updates_return("v1.0.0", "https://example.com/release", "", True)
        assert app._check_for_updates_menu.callback == app._check_for_updates_menu_cb
        assert app._check_for_updates_menu.title == "Check for updates..."
        assert mocked_dialog.called
        mocked_dialog.assert_called_once_with(
            "v1.0.0", "v0.2.0", "https://example.com/release", ""
        )

        # Check update invocation via timer
        mocked_update.reset_mock()
        app._startup_update_check_timer_cb(app._startup_update_check_timer)
        mocked_update.assert_called_once_with(
            "v0.2.0", app.check_for_updates_return, True
        )
        assert app._check_for_updates_menu.callback == None
        assert app._check_for_updates_menu.title == "Checking for updates..."

    def test_check_for_updates_no_new_version(self, mocked_app, mocker):
        app, _, _ = mocked_app()
        mocked_dialog = mocker.MagicMock()
        mocker.patch("pingrthingr.app.update_dialog", mocked_dialog)
        mocker.patch("pingrthingr.app.__VERSION__", "v0.2.0")

        # Not quiet, should call runner to display results
        app.check_for_updates_return("", "", "v0.2.0 is the latest version.", False)
        mocked_dialog.assert_called_once_with(
            "", "v0.2.0", "", "v0.2.0 is the latest version."
        )

        # Quiet, should not call runner
        mocked_dialog.reset_mock()
        app.check_for_updates_return("", "", "v0.2.0 is the latest version.", True)
        assert (
            not mocked_dialog.called
        ), "Runner should not be called when quiet is True and no new version"

    def test_check_for_updates_on_startup_enabled(self, mocked_app):
        # Test that the update timer starts on app initialization when setting is enabled
        settings = {"check_for_updates": True}
        app, _, _ = mocked_app(settings)
        assert (
            app._startup_update_check_timer.is_alive()
        ), "Update timer should be started when check_for_updates is True"

    def test_check_for_updates_on_startup_disabled(self, mocked_app):
        # Test that the update timer does not start on app initialization when setting is disabled
        settings = {"check_for_updates": False}
        app, _, _ = mocked_app(settings)
        assert (
            not app._startup_update_check_timer.is_alive()
        ), "Update timer should not be started when check_for_updates is False"

    def test_check_for_updates_on_startup_toggle(self, mocked_app):
        # Test that toggling the check_for_updates setting starts/stops the update timer
        settings = {"check_for_updates": False}
        app, _, _ = mocked_app(settings)
        assert (
            app._settings.get("check_for_updates") == False
        ), "Initial setting should be False"
        assert (
            app._check_for_updates_on_startup_menu.state == False
        ), "Menu state should reflect initial setting"
        app._check_for_updates_on_startup_menu.callback(
            app._check_for_updates_on_startup_menu
        )  # Toggle the setting
        assert (
            app._settings.get("check_for_updates") == True
        ), "Setting should be toggled to True"
        assert (
            app._check_for_updates_on_startup_menu.state == True
        ), "Menu state should reflect toggled setting"


class TestIconRendering:
    def test_nsview_clearance(self, mocked_app, mocker):

        app, _, mock_nsapp = mocked_app()

        icon, view, _ = generate_status_icon(
            "Text",
            latency=100,
            loss=0,
            latency_thresholds=ThresholdModel(warn=80, alert=500, critical=1000),
            loss_thresholds=ThresholdModel(warn=0.0, alert=0.01, critical=0.25),
        )

        mock_nsapp.nsstatusitem.button().subviews.return_value = [
            mocker.Mock()
        ]  # Simulate existing subviews
        app._draw_icon(icon, view)
        assert (
            mock_nsapp.nsstatusitem.button()
            .subviews()[0]
            .removeFromSuperview.call_count
            == 1
        ), "Existing subviews should be removed when drawing a new icon"
