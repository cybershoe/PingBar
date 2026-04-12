"""PingrThingr macOS menu bar application.

This module contains the main application class for PingrThingr, a macOS menu bar
application that monitors network connectivity by pinging specified targets.
"""

import logging

logger = logging.getLogger(__name__)

from .version import __VERSION__
from rumps import App, clicked, MenuItem, separator, application_support
from os.path import join as path_join
from .pinger import Pinger
from .icons import symbol_icon, generate_status_icon
from .settings import SelectableMenu, ping_target_window, SettingsManager
from .updates import update_dialog, run_update_check
from objc import selector as objc_selector  # type: ignore
from Foundation import NSOperationQueue, NSBlockOperation, NSLayoutConstraint  # type: ignore
from AppKit import NSImage, NSView  # type: ignore


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
        self.ping_targets_menu = MenuItem("Set ping targets...", callback=self.ping_targets)        
        self.check_for_updates_menu = MenuItem("Check for updates...", callback=self.check_for_updates)  # Placeholder for future update checking functionality
        self.check_for_updates_on_startup = MenuItem("Check on startup", callback=lambda _: None)  # Placeholder for future update checking functionality
        self.pause_menu.state = self._settings.get("paused", False)

        self.menu = [
            self.statistics_menu,
            separator,
            self.pause_menu,
            separator,
            self.display_menu,
            self.ping_targets_menu,
            separator,
            self.check_for_updates_menu,
            self.check_for_updates_on_startup,
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

        logger.info(f"Initialized PingrThingr")

    def _run_in_app_thread(self, func, *args, **kwargs):
        """Run a function in the main application thread.

        Utility method to execute a given function with arguments on the main
        thread of the application. Useful for ensuring that UI updates and
        other main-thread-only operations are performed safely from background
        threads.

        Args:
            func (callable): The function to execute on the main thread.
            *args: Variable length argument list to pass to the function.
            **kwargs: Arbitrary keyword arguments to pass to the function.
        """
        operation = NSBlockOperation.blockOperationWithBlock_(
            lambda: func(*args, **kwargs)
        )
        NSOperationQueue.mainQueue().addOperation_(operation)

    def pause_cb(self, paused: bool) -> None:
        """Callback for pause setting changes.

        Updates the pinger's running state and menu display when the pause
        setting is changed through the settings manager.

        Args:
            paused (bool): True to pause the pinger, False to resume.
        """
        logging.debug(f"In pause_cb(): Setting pinger running state to {not paused}")
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

        self._run_in_app_thread(self.refresh_status_, latency, loss)

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

    @objc_selector
    def refresh_status_(
        self,
        latency: float | None = None,
        loss: float | None = None,
        use_saved: bool = False,
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
            self._icon_nsimage = symbol_icon("pause.circle", "Paused")
            self._nsapp.setStatusBarIcon()
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
                self._last_state,
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
        """Check for application updates.

        Placeholder method for future implementation of update checking functionality.
        Currently displays a dialog with the latest version information.

        Args:
            sender (MenuItem): The menu item that was clicked to trigger the update check.
        """

        sender.set_callback(None)  # Disable the menu item while checking for updates
        sender.title = "Checking for updates..."
        run_update_check(__VERSION__, self.check_for_updates_return, False)

    def check_for_updates_return(self, new_version: str, release_url: str, error: str) -> None:
        self.check_for_updates_menu.set_callback(self.check_for_updates)
        self.check_for_updates_menu.title = "Check for updates..."
        logging.debug(f"Update check returned: new_version={new_version}, release_url={release_url}, error={error}")
        self._run_in_app_thread(update_dialog, new_version, __VERSION__, release_url, error)