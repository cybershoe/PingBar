"""PingrThingr macOS menu bar application.

This module contains the main application class for PingrThingr, a macOS menu bar
application that monitors network connectivity by pinging specified targets.
"""

import logging

logger = logging.getLogger(__name__)

from .version import __VERSION__
from .about import show_about_window
from rumps import App, MenuItem, Timer, separator, application_support
from os.path import join as path_join
from .pinger import Pinger
from .icons import symbol_icon, generate_status_icon
from .settings import SelectableMenu, ping_target_window, SettingsManager
from .updates import update_dialog, run_update_check
from AppKit import NSImage, NSView, NSPoint, NSObject, NSAppearanceNameAqua, NSAppearanceNameDarkAqua  # type: ignore
from pickle import dumps as pickle_dumps, loads as pickle_loads  # type: ignore


class PingrThingrApp(App):
    """Main application class for PingrThingr menu bar app.

    Extends the rumps.App class to provide a macOS menu bar application
    for network connectivity monitoring. Manages settings persistence
    and provides user interface controls for the pinger functionality.

    Attributes:
        pinger (Pinger): The network pinger instance.
        _settings (SettingsManager): Persistent application settings manager.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the PingrThingr application.

        Sets up the menu bar application with default settings, creates the
        status menu items, initializes the pinger, and loads any saved
        configuration from the settings file.

        Args:
            *args: Variable length argument list passed to parent App class.
            **kwargs: Arbitrary keyword arguments passed to parent App class.
        """
        super(PingrThingrApp, self).__init__(*args, **kwargs)
        self._settings_path = path_join(application_support(self.name), "settings.json")
        logger.debug(f"In __init__(): Settings file path: {self._settings_path}")
        self._settings = SettingsManager(self._settings_path)
        self.latency = None
        self.loss = None
        self.title = None
        self._appearance = None
        self._icon_nsimage = symbol_icon(
            (
                "pause.circle"
                if self._settings.get("paused", False)
                else "waveform.path.ecg"
            ),
            "PingrThingr",
        )

        # Initialize menu items
        self._statistics_menu = MenuItem("---")
        self._pause_menu = MenuItem("Pause", callback=self._pause_menu_cb)
        self._display_menu = SelectableMenu(
            "Display Mode",
            options=["Dot", "Text", "Chart"],
            selected=self._settings.get("display_mode", "Dot"),
            callback=self._display_menu_cb,
        )
        self._ping_targets_menu = MenuItem(
            "Set ping targets...", callback=self._ping_targets_menu_cb
        )
        self._check_for_updates_menu = MenuItem(
            "Check for updates...", callback=self._check_for_updates_menu_cb
        )
        self._check_for_updates_on_startup_menu = MenuItem(
            "Check on startup", callback=self._check_for_updates_on_startup_menu_cb
        )
        self._about_menu = MenuItem("About PingrThingr", callback=show_about_window)

        self._pause_menu.state = self._settings.get("paused", False)
        self._check_for_updates_on_startup_menu.state = self._settings.get(
            "check_for_updates", False
        )

        self.menu = [
            self._statistics_menu,
            separator,
            self._pause_menu,
            separator,
            self._display_menu,
            self._ping_targets_menu,
            separator,
            self._check_for_updates_menu,
            self._check_for_updates_on_startup_menu,
            separator,
            self._about_menu,
            separator
        ]
        self._last_state = None

        self._pinger = Pinger(
            targets=self._settings.get("targets", []),  # type: ignore
            start_running=not self._settings.get("paused", False),
            cb=self.update_statistics_cb,
        )

        self._settings.register_callback("paused", self.pause_settings_cb)
        self._settings.register_callback("targets", self.ping_targets_settings_cb)
        self._settings.register_callback("display_mode", self.display_mode_settings_cb)

        self._startup_update_check_timer = Timer(
            self._startup_update_check_timer_cb, 2
        )  # Update every 2 seconds
        self._ns_init_timer = Timer(
            self._ns_init_timer_cb, 0.1
        )  # Short delay to ensure NSApp is initialized
        self._ns_init_timer.start()
        if self._settings.get("check_for_updates", False):
            logger.debug(
                f"In __init__(): Check for updates on startup is enabled, starting update timer"
            )
            self._startup_update_check_timer.start()
        else:
            logger.debug(
                f"In __init__(): Check for updates on startup is disabled, not starting update timer"
            )

        logger.info(f"In __init__(): Initialized PingrThingr")

    # NSObject subclasses for KVO and main thread dispatching

    # class AppearanceObserver(NSObject):
    #     """KVO observer that reacts to system appearance changes.

    #     Registered on the status-bar button's effectiveAppearance key path
    #     so that the status icon is redrawn whenever the user switches between
    #     light and dark mode.
    #     """

    #     def observeValueForKeyPath_ofObject_change_context_(
    #         self, keyPath, obj, change, context
    #     ):  # pragma: no cover
    #         """Handle a KVO notification for a watched key path.

    #         Args:
    #             keyPath (str): The key path that changed.
    #             obj: The object whose property changed.
    #             change (dict): Dictionary describing the change.
    #             context: Arbitrary context pointer passed at registration time.
    #         """

    #         if keyPath == "effectiveAppearance":
    #             new_appearance = obj.effectiveAppearance().bestMatchFromAppearancesWithNames_(
    #                 [NSAppearanceNameDarkAqua, NSAppearanceNameAqua]
    #             )
    #             if new_appearance != self._app._appearance:
    #                 logger.debug(f"In observeValueForKeyPath_ofObject_change_context_(): Effective appearance changed from {self._app._appearance} to {new_appearance}")
    #                 self._app._appearance = new_appearance
    #                 #self._app._run_in_main_thread(
    #                     #"refresh_status_", use_saved=True, force=True
    #                 #)  # re-draw your icon or update colors here
    #             else:
    #                 logger.debug(
    #                     f"In observeValueForKeyPath_ofObject_change_context_(): Appearance did not change"
    #                 )

    class MainThreadDispatcher(NSObject):
        """NSObject shim used to dispatch calls onto the main run-loop thread.

        Because PingrThingrApp is not an NSObject subclass it cannot be the
        target of performSelectorOnMainThread. This lightweight wrapper holds
        a back-reference (_app) and forwards pickled call descriptors to the
        application instance.
        """

        def dispatchSelector_(self, userdata):
            """Receive a pickled call descriptor and execute it on the main thread.

            Invoked by the Objective-C runtime via
            performSelectorOnMainThread_withObject_waitUntilDone_. Unpickles
            the function name and arguments, looks up the method on the
            application instance, and calls it.

            Args:
                userdata (bytes): Pickled dict with keys ``func`` (str),
                    ``args`` (tuple), and ``kwargs`` (dict).
            """

            try:
                user_info = pickle_loads(userdata)
            except Exception as e:
                logger.error(
                    f"In dispatchSelector_(): Error unpickling userdata from selector: {e}"
                )
                return
            else:
                logger.debug(f"Successfully unpickled userdata: {user_info}")

            func = getattr(self._app, user_info.get("func", None), None)

            if func is None:
                raise KeyError(f"Function name not found in userdata: {user_info}")
            else:
                logger.debug(
                    f"In dispatchSelector_(): Retrieved function '{func.__name__}' from userdata"
                )

            args = user_info.get("args", ())
            kwargs = user_info.get("kwargs", {})

            logger.debug(
                f"Running function from userdata: {func.__name__} with args {args} and kwargs {kwargs}"
            )
            func(*args, **kwargs)

    # Timer callbacks

    def _ns_init_timer_cb(self, sender):  # pragma: no cover
        """Perform deferred NSApp-dependent initialisation.

        Called once by a short-delay rumps Timer after the application has
        started, ensuring NSApp and the status-bar item are fully available
        before KVO observers and the main-thread dispatcher are set up.

        Args:
            sender (Timer): The one-shot Timer that fired this callback.
        """
        sender.stop()
        self._dispatcher = self.MainThreadDispatcher.alloc().init()
        self._dispatcher._app = self
        # self.appearance_observer = self.AppearanceObserver.alloc().init()
        # self.appearance_observer._app = self
        # self._nsapp.nsstatusitem.button().addObserver_forKeyPath_options_context_(
        #     self.appearance_observer, "effectiveAppearance", 0, None
        # )

    def _startup_update_check_timer_cb(self, sender) -> None:
        """Handle startup update check timer expiration.

        Called by the Timer when the application starts up to perform an automatic
        update check if enabled in settings. This provides a delayed, non-blocking
        way to check for updates after the application is fully initialized.

        Args:
            sender (Timer): The Timer object that triggered this callback
        """
        self._check_for_updates_menu.set_callback(None)
        self._check_for_updates_menu.title = "Checking for updates..."
        sender.stop()
        run_update_check(__VERSION__, self.check_for_updates_return, True)

    # Menu callbacks

    def _ping_targets_menu_cb(self, _) -> None:
        """Handle ping targets menu item click.

        Displays the preferences dialog for configuring ping target IP addresses.
        If the user saves changes, updates the application settings with the new
        target list.

        Args:
            _ (MenuItem): Unused menu item parameter (required by rumps framework).
        """
        new_targets = ping_target_window(self._settings.get("targets", []))  # type: ignore
        if new_targets is not None:
            logger.debug(
                f"In _ping_targets_menu_cb(): Updating targets from ping_target_window(): {new_targets}"
            )
            self._settings.set("targets", new_targets)
        else:
            logger.debug(
                f"In _ping_targets_menu_cb(): ping_target_window() returned None, no changes to targets"
            )

    def _pause_menu_cb(self, sender) -> None:
        """Toggle the pinger pause state.

        Toggles between paused and running states for the network pinger.
        Updates the menu item state and persists the change to settings.

        Args:
            sender (MenuItem): The pause menu item that was clicked.
        """
        logger.debug(
            f"In _pause_menu_cb(): Toggling pause state from {sender.state} to {not sender.state}"
        )

        self._settings.set("paused", not sender.state)

    def _display_menu_cb(self, sender) -> None:
        """Handle display mode menu selection.

        Updates the display mode setting based on the user's selection in the
        "Display Mode" submenu. The SelectableMenu component handles the menu
        state and title updates, so this callback only needs to persist the
        selected value to settings.

        Args:
            sender (SelectableMenu): The SelectableMenu instance that triggered this callback.
        """
        new_selection = sender.get_selected()
        logger.debug(
            f"In _display_menu_cb(): Updating display_mode setting to {new_selection}"
        )
        self._settings.set("display_mode", new_selection)

    def _check_for_updates_menu_cb(self, sender) -> None:
        """Initiate a manual check for application updates.

        Temporarily disables the menu item and starts an asynchronous update check
        process. The menu item is re-enabled when the check completes via the
        check_for_updates_return callback method.

        Args:
            sender (MenuItem): The "Check for updates..." menu item that was clicked
        """

        sender.set_callback(None)  # Disable the menu item while checking for updates
        sender.title = "Checking for updates..."
        run_update_check(__VERSION__, self.check_for_updates_return, False)

    def _check_for_updates_on_startup_menu_cb(self, sender) -> None:
        """Toggle the "Check on startup" setting.

        Updates the application settings to enable or disable automatic update checks
        on application startup based on the menu item state.

        Args:
            sender (MenuItem): The "Check on startup" menu item that was clicked
        """
        sender.state = not sender.state
        self._settings.set("check_for_updates", sender.state)

    # Settings callbacks

    def pause_settings_cb(self, paused: bool) -> None:
        """Callback for pause setting changes.

        Updates the pinger's running state and menu display when the pause
        setting is changed through the settings manager.

        Args:
            paused (bool): True to pause the pinger, False to resume.
        """
        logger.debug(
            f"In pause_settings_cb(): Setting pinger running state to {not paused}"
        )
        self._pinger.run(not paused)
        self._pause_menu.state = paused
        if paused:  # pragma: no cover
            self.latency = None
            self.loss = None
        self.refresh_status_(use_saved=True, force=True)

    def ping_targets_settings_cb(self, targets: list[str]) -> None:
        """Callback for ping targets setting changes.

        Updates the pinger's target list when the targets setting is changed
        through the settings manager.

        Args:
            targets (list[str]): List of IP addresses to ping.
        """
        self._pinger.targets = targets

    def display_mode_settings_cb(self, display_mode: str) -> None:
        """Callback for display mode setting changes.

        Updates the status icon display mode when the display_mode setting is
        changed through the settings manager.

        Args:
            display_mode (str): The new display mode ("Dot" or "Text").
        """
        self.refresh_status_(use_saved=True, force=True)

    def update_statistics_cb(
        self, latency: float | None = None, loss: float | None = None
    ) -> None:
        """Update the statistics display with new network measurements.

        Called by the pinger when new latency and packet loss measurements
        are available. Updates internal state and triggers a display refresh.

        Args:
            latency (float, optional): The average latency in milliseconds. Defaults to None.
            loss (float, optional): The packet loss as a decimal (0.0-1.0). Defaults to None.
        """

        logger.debug(
            f"In update_statistics_cb(): Updating statistics: loss={loss}, latency={latency}"
        )

        self._run_in_main_thread("refresh_status_", latency, loss)

    # Icon and menu update methods

    def _draw_icon(self, icon: NSImage, view: NSView | None = None) -> None:
        """Update the menu bar icon.

        Stores the provided NSImage and instructs the rumps NSApp wrapper to
        apply it to the status-bar item.

        Args:
            icon (NSImage): The icon to display in the menu bar.
        """

        logger.debug(f"In _draw_icon(): Drawing icon from NSImage")
        self._icon_nsimage = icon
        self._icon_nsview = view

        for oldview in list(self._nsapp.nsstatusitem.button().subviews()):
            oldview.removeFromSuperview()


        self._nsapp.setStatusBarIcon()
        if view is not None:
            logger.debug(f"In _draw_icon(): Adding custom NSView to status bar button")
            button_size = self._nsapp.nsstatusitem.button().bounds().size
            view_size = view.frame().size
            x_offset = (button_size.width - view_size.width) / 2
            y_offset = (button_size.height - view_size.height) / 2
            view.setFrameOrigin_(NSPoint(x_offset, y_offset))
            self._nsapp.nsstatusitem.button().addSubview_(view)


    def refresh_status_(
        self,
        latency: float | None = None,
        loss: float | None = None,
        use_saved: bool = False,
        force: bool = False,
    ) -> None:
        """Refresh the status icon and dynamic menu text.

        Updates the menu item text with current network statistics and
        refreshes the menu bar icon based on the current display mode
        and network connectivity status. Must be called on the main thread;
        use ``_run_in_main_thread`` to dispatch from background threads.

        Args:
            latency (float | None, optional): Current latency in milliseconds.
                                            Defaults to None.
            loss (float | None, optional): Current packet loss ratio (0.0-1.0).
                                         Defaults to None.
            use_saved (bool, optional): If True, ignores ``latency`` and ``loss``
                                      and reuses the last stored values instead.
                                      Defaults to False.
            force (bool, optional): If True, bypasses the last-state cache and
                                   always redraws the icon even when the state
                                   has not changed. Defaults to False.
        """
        if use_saved:
            latency = self.latency
            loss = self.loss
        else:
            self.latency = latency
            self.loss = loss

        if self._settings.get("paused"):
            logger.debug(
                f"In refresh_status_(): Application is paused, showing paused status"
            )
            self._statistics_menu.title = "Paused"
            self._draw_icon(symbol_icon("pause.circle", "Paused"))

        else:
            logger.debug(
                f"In refresh_status_(): Application is running, showing latency and loss"
            )
            loss_str = f"{(loss*100):.2f}%" if loss is not None else "---"
            latency_str = f"{(latency):.2f} ms" if latency is not None else "---"
            self._statistics_menu.title = f"Loss: {loss_str}, Latency: {latency_str}"
            display = self._settings.get("display_mode", "Dot")
            logger.debug(f"In refresh_status_(): Current display_mode: {display}")

            icon, view, new_state = generate_status_icon(  # type: ignore
                display,  # type: ignore
                latency,
                loss,
                self._settings.get("latency_thresholds"),  # type: ignore
                self._settings.get("loss_thresholds"),  # type: ignore
                self._last_state,
                # self._nsapp.nsstatusitem.button().effectiveAppearance(),
                force=force
            )

            logger.debug(
                f"In refresh_status_(): Last state: {self._last_state}, new state: {new_state}"
            )
            self._last_state = new_state

            if icon is not None:
                logger.debug(
                    f"In refresh_status_(): Updating icon for new state: {new_state}"
                )
                self._draw_icon(icon, view)

    # Update check return handling methods

    def check_for_updates_return(
        self, new_version: str, release_url: str, error: str, quiet: bool = False
    ) -> None:
        """Handle the callback from update checking process.

        This method is called when the update check completes (successfully or with error).
        It restores the update menu item to its normal state and displays the appropriate
        update dialog with the results.

        Args:
            new_version (str): New version string if available, empty string otherwise
            release_url (str): URL to the GitHub release page if update available
            error (str): Error message if update check failed, empty string on success
            quiet (bool, optional): If True, suppresses update dialog if no update is available.
                                    Defaults to False.
        """
        self._check_for_updates_menu.set_callback(self._check_for_updates_menu_cb)
        self._check_for_updates_menu.title = "Check for updates..."
        logger.debug(
            f"Update check returned: new_version={new_version}, release_url={release_url}, error={error}"
        )

        if new_version or not quiet:
            self._run_in_main_thread(
                "_update_dialog_return", new_version, __VERSION__, release_url, error
            )

    def _update_dialog_return(
        self, new_version: str, current_version, release_url: str, error: str
    ) -> None:
        """Display the update dialog on the main thread.

        This thin wrapper exists so that ``check_for_updates_return`` can
        dispatch the dialog to the main thread via ``_run_in_main_thread``.

        Args:
            new_version (str): Latest version string, or empty if none available.
            current_version (str): Currently installed version string.
            release_url (str): URL to the GitHub release page for the new version.
            error (str): Error message if the update check failed, empty on success.
        """
        update_dialog(new_version, current_version, release_url, error)

    # Main thread dispatching method

    def _run_in_main_thread(self, func: str, *args, **kwargs):
        """Schedule a method to execute on the main application thread.

        Serialises the method name and arguments via pickle and dispatches
        the call through ``MainThreadDispatcher`` using
        ``performSelectorOnMainThread_withObject_waitUntilDone_``. This
        avoids cross-thread PyObjC retain cycles that arise when Python
        objects are passed directly as NSTimer userInfo.

        Safe to call from any thread, including the pinger background thread.

        Args:
            func (str): Name of a method on this application instance to call.
            *args: Positional arguments forwarded to the method.
            **kwargs: Keyword arguments forwarded to the method.
        """
        logger.debug(
            f"In _run_in_main_thread(): Scheduling refresh to run {func} in app thread with args: {args} and kwargs: {kwargs}"
        )

        # non-scalar values in userdata seem to cause memory leaks between python and objc
        userdata = pickle_dumps({"func": func, "args": args, "kwargs": kwargs})

        self._dispatcher.performSelectorOnMainThread_withObject_waitUntilDone_(
            "dispatchSelector:", userdata, False
        )
