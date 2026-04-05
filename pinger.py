"""Network pinger module for monitoring network connectivity.

This module provides the Pinger class which performs periodic network pings
to specified IP addresses to monitor connectivity status.
"""

import logging

logger = logging.getLogger(__name__)

from asyncio import (
    AbstractEventLoop,
    set_event_loop,
    new_event_loop,
    run_coroutine_threadsafe,
    sleep as asyncio_sleep,
    wait_for,
    CancelledError,
    TimeoutError,
)
from typing import List
from threading import Thread
from socket import inet_aton
from time import monotonic
from icmplib import async_multiping


class Pinger:
    """A network pinger class that periodically monitors connectivity to target IP addresses.

    This class runs a background async task that performs periodic connectivity checks
    to a list of target IP addresses. The pinger runs in its own event loop on a
    separate daemon thread to avoid blocking the main application.

    Attributes:
        frequency (int): Time in seconds between ping cycles.
        targets (List[str]): List of IP addresses to monitor.
        cb (callable): Optional callback function called with ping results.
    """

    def __init__(
        self,
        targets: List[str] = [],
        timeout: int = 2,
        count: int = 10,
        interval: float = 0.5,
        frequency: int = 10,
        start_running: bool = False,
        cb: callable = None,
    ):
        """Initialize the Pinger instance.

        Creates a new pinger with the specified configuration and optionally
        starts monitoring immediately. Validates all target IP addresses and
        sets up a background thread with its own async event loop.

        Args:
            targets (List[str], optional): List of IPv4 addresses to ping. Defaults to [].
            timeout (int, optional): Ping timeout in seconds. Defaults to 2.
            count (int, optional): Number of ping packets per target per cycle. Defaults to 10.
            interval (float, optional): Time between individual ping packets in seconds. Defaults to 0.5.
            frequency (int, optional): Time between ping cycles in seconds. Defaults to 10.
            start_running (bool, optional): Whether to start pinging immediately. Defaults to False.
            cb (callable, optional): Callback function for ping results (latency, loss). Defaults to None.

        Raises:
            ValueError: If any target IP address is invalid.
        """

        self._targets = []
        self.targets = targets
        self._frequency = frequency
        self._timeout = timeout
        self._count = count
        self._interval = interval
        self.cb = cb

        self.loop = new_event_loop()
        Thread(
            target=self._start_background_loop, args=(self.loop,), daemon=True
        ).start()
        self.pinger_coroutine = None

        logger.info(f"Pinger initialized")
        logger.debug(
            f"In __init__(): Configuration - timeout: {timeout}, count: {count}, interval: {interval}, frequency: {frequency}"
        )
        if start_running:
            self.run(True)  # Start in the running state

    def __del__(self):
        """Clean up resources when the Pinger instance is destroyed.

        Attempts to stop the background event loop gracefully.
        """
        logger.debug(
            "Pinger instance is being destroyed, attempting to stop background loop"
        )
        try:
            self.loop.call_soon_threadsafe(self.loop.stop)
        except AttributeError:
            pass  # loop may not exist if __init__ failed

    def _start_background_loop(self, loop: AbstractEventLoop) -> None:
        """Start the background event loop for async operations.

        This method runs in a separate daemon thread to handle async ping operations
        without blocking the main application thread.

        Args:
            loop (AbstractEventLoop): The asyncio event loop to run.
        """
        logger.debug(
            "In _start_background_loop(): Starting background event loop for Pinger"
        )
        set_event_loop(loop)
        loop.run_forever()

    @property
    def targets(self) -> List[str]:
        """Get the list of target IP addresses.

        Returns:
            List[str]: List of IP addresses being monitored.
        """
        return self._targets

    @targets.setter
    def targets(self, targets: List[str]) -> None:
        """Set the list of target IP addresses to monitor.

        Validates that all provided addresses are valid IPv4 addresses.

        Args:
            targets (List[str]): List of IP addresses to monitor.

        Raises:
            ValueError: If any target IP address is invalid.
        """

        try:
            for target in targets:
                inet_aton(target)
        except OSError:
            raise ValueError(f"Invalid IP address: {target}")
        else:
            self._targets = targets
            logger.info(f"Updated target IP addresses: {self._targets}")

    async def _run_pings(self) -> None:
        """Background async task that performs periodic ping operations.

        This coroutine runs continuously, performing ping operations at the
        specified frequency interval. Executes the callback function with
        results if one is provided. It can be cancelled by calling run(False).

        Raises:
            asyncio.CancelledError: When the task is cancelled.
        """
        try:
            while True:
                start_time = monotonic()
                if len(self.targets) > 0:
                    logger.debug(f"In _run_pings(): Pinging targets: {self._targets}")
                    try:
                        results = await wait_for(
                            async_multiping(
                                self._targets,
                                count=self._count,
                                timeout=self._timeout,
                                interval=self._interval,
                                privileged=False,
                                concurrent_tasks=20,
                            ),
                            timeout=30.0,
                        )
                        if logger.isEnabledFor(logging.DEBUG):
                            ping_results = [
                                {
                                    "target": r.address,
                                    "avg_rtt": r.avg_rtt,
                                    "packet_loss": r.packet_loss,
                                }
                                for r in results
                            ]
                            logger.debug(
                                "In _run_pings(): Ping results: %s", ping_results
                            )

                        if self.cb:
                            try:
                                avg_latency = self.remove_outliers_and_avg(
                                    [
                                        host.avg_rtt
                                        for host in results
                                        if host.avg_rtt is not None
                                    ]
                                )
                                avg_loss = self.remove_outliers_and_avg(
                                    [
                                        host.packet_loss
                                        for host in results
                                        if host.packet_loss is not None
                                    ]
                                )
                                self.cb(avg_latency, avg_loss)
                            except Exception as e:
                                logger.error(f"Error in callback function: {e}")

                    except TimeoutError:
                        logger.warning("Ping operation timed out after 30 seconds")
                    except Exception as e:
                        logger.error(f"Error occurred while pinging: {e}")
                else:
                    logger.info("No targets to ping")
                await asyncio_sleep(self._frequency - ((monotonic() - start_time)))
        except CancelledError:
            logger.debug("In _run_pings(): Ping task was cancelled")

    def run(self, running: bool) -> None:
        """Start or stop the ping monitoring.

        Controls the ping monitoring state. When starting, creates a new
        asynchronous ping task. When stopping, cancels any running task
        and calls the callback with None values to indicate stopped state.

        Args:
            running (bool): True to start pinging, False to stop pinging.
        """
        if running:
            logger.info("Starting ping monitoring")
            if self.pinger_coroutine is None:
                self.pinger_coroutine = run_coroutine_threadsafe(
                    self._run_pings(), self.loop
                )
            else:
                logger.warning(
                    "Attempted to start ping monitoring, but it is already running"
                )
        else:
            logger.info("Stopping ping monitoring")
            if self.pinger_coroutine is not None:
                self.pinger_coroutine.cancel()
                self.pinger_coroutine = None
            else:
                logger.warning(
                    "Attempted to stop ping monitoring, but no ping task was running"
                )
            if self.cb:
                self.cb(None, None)

    def remove_outliers_and_avg(self, values: List[float]) -> float | None:
        """Remove outlier values and return the mean of remaining values.

        This method filters out values that are significantly higher than the mean.
        If no values are provided, it returns None. If only one value is provided,
        it returns that value. Otherwise, it calculates the mean and removes any
        value that is more than 1.5 times the mean, then returns the new mean.

        Args:
            values (List[float]): List of float values to filter for outliers.

        Returns:
            float | None: Mean of filtered values, or None if no values provided.
        """
        logger.debug(
            f"In remove_outliers_and_avg(): Removing outliers from values: {values}"
        )
        if len(values) == 0:
            logger.debug(
                "In remove_outliers_and_avg(): No values provided, returning None"
            )
            return None
        elif len(values) == 1:
            logger.debug(
                f"In remove_outliers_and_avg(): Only one value provided, returning that value: {values[0]}"
            )
            return values[0]
        else:
            mean_value = sum(values) / len(values)
            max_value = max(values)
            if max_value > mean_value * 1.5:
                logger.debug(
                    f"In remove_outliers_and_avg(): Removing outlier {max_value}"
                )
                values.pop(values.index(max_value))  # Remove max value as outlier
                filtered_mean = sum(values) / len(values)
                logger.debug(
                    f"In remove_outliers_and_avg(): Returning filtered mean value: {filtered_mean}"
                )
                return filtered_mean
            else:
                logger.debug(
                    f"In remove_outliers_and_avg(): No outliers detected, returning mean of all values: {mean_value}"
                )
                return mean_value
