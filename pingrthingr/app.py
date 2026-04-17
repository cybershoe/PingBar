"""PingrThingr macOS menu bar application.

This module contains the main application class for PingrThingr, a macOS menu bar
application that monitors network connectivity by pinging specified targets.
"""

import logging

logger = logging.getLogger(__name__)

from .version import __VERSION__
from rumps import App, MenuItem, Timer, separator, application_support
from os.path import join as path_join
from .pinger import Pinger
from .icons import symbol_icon, generate_status_icon
from .settings import SelectableMenu, ping_target_window, SettingsManager
from .updates import update_dialog, run_update_check
from Foundation import NSTimer, NSRunLoop  # type: ignore
from AppKit import NSImage, NSView, NSObject  # type: ignore
import gc
from pickle import dumps as pickle_dumps, loads as pickle_loads  # type: ignore


class PingrThingrApp(App):
    """Main application class for PingrThingr menu bar app.

    Extends the rumps.App class to provide a macOS menu bar application
    for network connectivity monitoring. Manages settings persistence
    and provides user interface controls for the pinger functionality.

    Attributes:
        pinger (Pinger): The network pinger instance.
        settings (dict): Application settings dictionary.
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
        logger.debug(f"Settings file path: {self._settings_path}")
        self._settings = SettingsManager(self._settings_path)
        self.latency = None
        self.loss = None
        self.title = None
        self._icon_nsimage = symbol_icon(
            (
                "pause.circle"
                if self._settings.get("paused", False)
                else "waveform.path.ecg"
            ),
            "PingrThingr",
        )
        self.statistics_menu = MenuItem("---")
        self.pause_menu = MenuItem("Pause", callback=self.pause_toggle)
        self.display_menu = SelectableMenu(
            "Display Mode",
            options=["Dot", "Text"],
            selected=self._settings.get("display_mode", "Dot"),
            cb=lambda x: self._settings.set("display_mode", x),
        )
        self.ping_targets_menu = MenuItem(
            "Set ping targets...", callback=self.ping_targets
        )
        self.check_for_updates_menu = MenuItem(
            "Check for updates...", callback=self.check_for_updates
        )  # Placeholder for future update checking functionality
        self.check_for_updates_on_startup_menu = MenuItem(
            "Check on startup", callback=self.check_for_updates_on_startup
        )  # Placeholder for future update checking functionality
        self.pause_menu.state = self._settings.get("paused", False)
        self.check_for_updates_on_startup_menu.state = self._settings.get(
            "check_for_updates", False
        )

        self.menu = [
            self.statistics_menu,
            separator,
            self.pause_menu,
            separator,
            self.display_menu,
            self.ping_targets_menu,
            separator,
            self.check_for_updates_menu,
            self.check_for_updates_on_startup_menu,
            separator,
        ]
        self._last_state = None

        self.pinger = Pinger(
            targets=self._settings.get("targets", []),  # type: ignore
            start_running=not self._settings.get("paused", False),
            cb=self.update_statistics,
        )

        self._settings.register_callback("paused", self.pause_cb)
        self._settings.register_callback("targets", self.ping_targets_cb)
        self._settings.register_callback(
            "display_mode", lambda _: self.refresh_status_(use_saved=True)
        )

        self._update_timer = Timer(self.update_timer, 2)  # Update every 2 seconds
        self._ns_init_timer = Timer(self.ns_init_timer, 0.1)  # Short delay to ensure NSApp is initialized
        self._ns_init_timer.start()
        if self._settings.get("check_for_updates", False):
            logger.debug(f"Check for updates on startup is enabled, starting update timer")
            self._update_timer.start()
        else:
            logger.debug(f"Check for updates on startup is disabled, not starting update timer")


        logger.info(f"Initialized PingrThingr")

    def ns_init_timer(self, sender):
        sender.stop()
        self.appearance_observer = self.AppearanceObserver.alloc().init()
        self._nsapp.nsstatusitem.button().addObserver_forKeyPath_options_context_(
            self.appearance_observer,
            "effectiveAppearance",
            0,
            None
        )
    class AppearanceObserver(NSObject):
        def observeValueForKeyPath_ofObject_change_context_(
            self, keyPath, obj, change, context
        ):
            logger.debug("in AppearanceObserver.observeValueForKeyPath_ofObject_change_context_")
            if keyPath == "effectiveAppearance":
                # super().refresh_status_(use_saved=True, force=True)
                # re-draw your icon or update colors here
                logger.debug(f"Appearance change detected, refreshing status icon")

    def run_in_timer(self, func: str, *args, **kwargs):
        """Run a function in the main application thread using a Timer.

        Schedules a function to be executed on the main thread using a one-shot
        Timer, to allow arguments to be passed between threads without orphaned
        references causing a emory leak.

        Args:
            func (callable): The function to execute on the main thread.
            *args: Variable length argument list to pass to the function.
            **kwargs: Arbitrary keyword arguments to pass to the function.
        """
        logger.debug(f"Scheduling refresh to run {func} in app thread with args: {args} and kwargs: {kwargs}")

        # non-scalar values in userdata seem to cause memory leaks between python and objc
        userdata = pickle_dumps({"func": func, "args": args, "kwargs": kwargs})

        timer = NSTimer.timerWithTimeInterval_target_selector_userInfo_repeats_(
            0.0, self, "_run_from_timer:", userdata, False
        )        
        NSRunLoop.mainRunLoop().addTimer_forMode_(timer, "NSDefaultRunLoopMode")

    def _run_from_timer_(self, timer):

        logger.debug(f"Running function from timer with userInfo: {timer.userInfo()}")

        try:
            user_info = pickle_loads(timer.userInfo())
        except Exception as e:
            logger.error(f"Error unpickling userInfo from timer: {e}")
            return
        else:
            logger.debug(f"Successfully unpickled userInfo: {user_info}")

        func=getattr(self, user_info.get('func', None), None)

        if func is None:
            raise KeyError(f"Function name not found in timer userInfo: {user_info}")
        else:
            logger.debug(f"Retrieved function '{func.__name__}' from timer userInfo")
        
        args=user_info.get('args', ())
        kwargs=user_info.get('kwargs', {})
        
        logger.debug(f"Running function from timer: {func.__name__} with args {args} and kwargs {kwargs}")
        func(*args, **kwargs)

        logger.debug(f"Total objects after running function: {len(gc.get_objects())}")

    def pause_cb(self, paused: bool) -> None:
        """Callback for pause setting changes.

        Updates the pinger's running state and menu display when the pause
        setting is changed through the settings manager.

        Args:
            paused (bool): True to pause the pinger, False to resume.
        """
        logger.debug(f"In pause_cb(): Setting pinger running state to {not paused}")
        self.pinger.run(not paused)
        self.pause_menu.state = paused
        if paused:  # pragma: no cover
            self.latency = None
            self.loss = None
        self.refresh_status_(use_saved=True)

    def ping_targets_cb(self, targets: list[str]) -> None:
        """Callback for ping targets setting changes.

        Updates the pinger's target list when the targets setting is changed
        through the settings manager.

        Args:
            targets (list[str]): List of IP addresses to ping.
        """
        self.pinger.targets = targets

    def update_statistics(
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
            f"In update_statistics(): Updating statistics: loss={loss}, latency={latency}"
        )

        self.run_in_timer("refresh_status_", latency, loss)

    def _draw_icon(self, icon: NSImage | NSView) -> None:
        """Draw the menu bar icon.

        Updates the macOS menu bar status item with either an NSImage or NSView icon.
        For NSView icons, adds the view as a subview to the status bar button and
        positions it appropriately within the button bounds.

        Args:
            icon (NSImage | NSView): The icon to display in the menu bar.
                                   Can be either an NSImage or NSView instance.

        Raises:
            TypeError: If icon is not an NSImage or NSView instance.
        """

        # Remove existing subview(s) if present
        if len(self._nsapp.nsstatusitem.button().subviews()) > 0:
            for i in range(len(self._nsapp.nsstatusitem.button().subviews())):
                self._nsapp.nsstatusitem.button().subviews()[i].removeFromSuperview()

        # Set icon to image if provided, otherwise blank backgrop for view
        if icon is not None and isinstance(icon, NSImage):
            logger.debug(f"Drawing icon from NSImage")
            self._icon_nsimage = icon
        elif icon is not None and isinstance(icon, NSView):
            blank_image = NSImage.alloc().initWithSize_(icon.frame().size)
            self._icon_nsimage = blank_image
        else:  # pragma: no cover
            raise TypeError(
                f"Invalid icon type: {type(icon)}. Expected NSImage or NSView."
            )

        self._nsapp.setStatusBarIcon()

        if isinstance(icon, NSView):
            logger.debug(f"Adding NSView as subview to status bar button")
            self._nsapp.nsstatusitem.button().addSubview_(icon)

            # Center the view within the button
            button_frame = self._nsapp.nsstatusitem.button().frame()
            icon_frame = icon.frame()
            offset_x = (button_frame.size.width - icon_frame.size.width) / 2
            offset_y = (button_frame.size.height - icon_frame.size.height) / 2
            icon.setFrameOrigin_((offset_x, offset_y))

    def refresh_status_(
        self,
        latency: float | None = None,
        loss: float | None = None,
        use_saved: bool = False,
        force: bool = False
    ) -> None:
        """Refresh the status icon and dynamic menu text.

        Updates the menu item text with current network statistics and
        refreshes the menu bar icon based on the current display mode
        and network connectivity status. This method is thread-safe and
        can be called from background threads.

        Args:
            latency (float | None, optional): Current latency in milliseconds.
                                            Defaults to None.
            loss (float | None, optional): Current packet loss ratio (0.0-1.0).
                                         Defaults to None.
            use_saved (bool, optional): Whether to use previously stored values
                                      instead of the provided parameters.
                                      Defaults to False.
        """
        if use_saved:
            latency = self.latency
            loss = self.loss
        else:
            self.latency = latency
            self.loss = loss

        if self._settings.get("paused"):
            logger.debug(
                f"In refresh_status(): Application is paused, showing paused status"
            )
            self.statistics_menu.title = "Paused"
            self._draw_icon(symbol_icon("pause.circle", "Paused"))
            
        else:
            logger.debug(
                f"In refresh_status(): Application is running, showing latency and loss"
            )
            loss_str = f"{(loss*100):.2f}%" if loss is not None else "---"
            latency_str = f"{(latency):.2f} ms" if latency is not None else "---"
            self.statistics_menu.title = f"Loss: {loss_str}, Latency: {latency_str}"
            display = self._settings.get("display_mode", "Dot")
            logger.debug(f"In refresh_status(): Current display_mode: {display}")

            icon, new_state = generate_status_icon(  # type: ignore
                display,  # type: ignore
                latency,
                loss,
                self._settings.get("latency_thresholds"),  # type: ignore
                self._settings.get("loss_thresholds"),  # type: ignore
                self._last_state if not force else None,
                self._nsapp.nsstatusitem.button().effectiveAppearance()
            )

            logger.debug(
                f"In refresh_status(): Last state: {self._last_state}, new state: {new_state}"
            )
            self._last_state = new_state

            if icon is not None:
                logger.debug(
                    f"In refresh_status(): Updating icon for new state: {new_state}"
                )
                self._draw_icon(icon)

    def ping_targets(self, _) -> None:
        """Handle ping targets menu item click.

        Displays the preferences dialog for configuring ping target IP addresses.
        If the user saves changes, updates the application settings with the new
        target list.

        Args:
            _ (MenuItem): Unused menu item parameter (required by rumps framework).
        """
        new_targets = ping_target_window(self._settings.get("targets", []))  # type: ignore
        if new_targets is not None:
            logger.debug(f"Updating targets from ping_target_window(): {new_targets}")
            self._settings.set("targets", new_targets)
        else:
            logger.debug(f"ping_target_window() returned None, no changes to targets")

    def pause_toggle(self, sender) -> None:
        """Toggle the pinger pause state.

        Toggles between paused and running states for the network pinger.
        Updates the menu item state and persists the change to settings.

        Args:
            sender (MenuItem): The pause menu item that was clicked.
        """
        logger.debug(f"Toggling pause state from {sender.state} to {not sender.state}")

        self._settings.set("paused", not sender.state)

    def check_for_updates(self, sender) -> None:
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
        self.check_for_updates_menu.set_callback(self.check_for_updates)
        self.check_for_updates_menu.title = "Check for updates..."
        logger.debug(
            f"Update check returned: new_version={new_version}, release_url={release_url}, error={error}"
        )

        if new_version or not quiet:
            self.run_in_timer(
                "_update_dialog_return", new_version, __VERSION__, release_url, error
            )

    def _update_dialog_return(self, new_version: str, current_version, release_url: str, error: str) -> None:
        update_dialog(new_version, current_version, release_url, error)


    def update_timer(self, sender) -> None:
        """Handle startup update check timer expiration.

        Called by the Timer when the application starts up to perform an automatic
        update check if enabled in settings. This provides a delayed, non-blocking
        way to check for updates after the application is fully initialized.

        Args:
            sender (Timer): The Timer object that triggered this callback
        """
        self.check_for_updates_menu.set_callback(None)
        self.check_for_updates_menu.title = "Checking for updates..."
        sender.stop()
        run_update_check(__VERSION__, self.check_for_updates_return, True)

    def check_for_updates_on_startup(self, sender) -> None:
        """Toggle the "Check on startup" setting.

        Updates the application settings to enable or disable automatic update checks
        on application startup based on the menu item state.

        Args:
            sender (MenuItem): The "Check on startup" menu item that was clicked
        """
        sender.state = not sender.state
        self._settings.set("check_for_updates", sender.state)
