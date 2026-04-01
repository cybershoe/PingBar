"""Network pinger module for monitoring network connectivity.

This module provides the Pinger class which performs periodic network pings
to specified IP addresses to monitor connectivity status.
"""

from asyncio import (
    AbstractEventLoop,
    set_event_loop,
    new_event_loop,
    run_coroutine_threadsafe,
    sleep as asyncio_sleep,
    wait_for,
    CancelledError,
    TimeoutError
)

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
        frequency (float): Time in seconds between ping cycles.
        targets (list[str]): List of IP addresses to monitor.
    """

    def __init__(self, targets=[], timeout: int = 2, count: int = 5, interval: float = 0.5, frequency: int = 2, start_running: bool = False):
        """Initialize the Pinger instance.
        
        Args:
            targets (list[str], optional): List of IP addresses to ping. Defaults to [].
            frequency (float, optional): Minimum time in seconds between ping cycles. Defaults to 2.0.
            start_running (bool, optional): Whether to start pinging immediately. Defaults to True.
        
        Raises:
            ValueError: If any target IP address is invalid.
        """

        self._targets = []
        self.targets = targets
        self._frequency = frequency
        self._timeout = timeout
        self._count = count
        self._interval = interval   

        self.loop = new_event_loop()
        Thread(
            target=self._start_background_loop, args=(self.loop,), daemon=True
        ).start()
        self.pinger_coroutine = None

        if start_running:
            self.run(True)  # Start in the running state

    def __del__(self):
        """Clean up resources when the Pinger instance is destroyed.
        
        Attempts to stop the background event loop gracefully.
        """
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
        set_event_loop(loop)
        loop.run_forever()

    @property
    def targets(self) -> list[str]:
        """Get the list of target IP addresses.
        
        Returns:
            list[str]: List of IP addresses being monitored.
        """
        return self._targets

    @targets.setter
    def targets(self, targets: list[str]) -> None:
        """Set the list of target IP addresses to monitor.
        
        Validates that all provided addresses are valid IPv4 addresses.
        
        Args:
            targets (list[str]): List of IP addresses to monitor.
            
        Raises:
            ValueError: If any target IP address is invalid.
        """
        for target in targets:
            try:
                inet_aton(target)
            except OSError:
                raise ValueError(f"Invalid IP address: {target}")
            else:
                self._targets = targets

    @targets.getter
    def targets(self) -> list[str]:
        """Get the list of target IP addresses.
        
        Returns:
            list[str]: List of IP addresses being monitored.
        """
        return self._targets

    async def _run_pings(self) -> None:
        """Background async task that performs periodic ping operations.
        
        This coroutine runs continuously, performing ping operations at the
        specified frequency interval. It can be cancelled by calling run(False).
        
        Raises:
            asyncio.CancelledError: When the task is cancelled.
        """
        try:
            while True:
                start_time = monotonic()
                if len(self.targets) > 0:
                    try:
                        results = await wait_for(
                            async_multiping(self._targets, count=self._count, timeout=self._timeout, interval=self._interval, privileged=False, concurrent_tasks=20),
                            timeout=30.0
                        )
                        for result in results:
                            print(f"Pinged {result.address}: avg {result.avg_rtt} ms, max {result.max_rtt} ms (loss {result.packet_loss*100}%)")
         
                    except TimeoutError:
                        print("Ping operation timed out after 30 seconds")
                    except Exception as e:
                        print(f"Error occurred while pinging: {e}")
                else:
                    print("No targets to ping")
                await asyncio_sleep(self._frequency - ((monotonic() - start_time)))
        except CancelledError:
            print("ping task was cancelled")

    async def _background_task(self) -> None:
        """Background async task that performs periodic ping operations.
        
        This coroutine runs continuously, performing ping operations at the
        specified frequency interval. It can be cancelled by calling run(False).
        
        Raises:
            asyncio.CancelledError: When the task is cancelled.
        """
        try:
            while True:
                start_time = monotonic()
                print("background task is running")
                await asyncio_sleep(0.5)  # Simulate work being done
                await asyncio_sleep(self.frequency - ((monotonic() - start_time)))
        except CancelledError:
            print("background task was cancelled")

    def run(self, running: bool) -> None:
        """Start or stop the ping monitoring.
        
        Args:
            running (bool): True to start pinging, False to stop pinging.
        """
        if running:
            if self.pinger_coroutine is None:
                self.pinger_coroutine = run_coroutine_threadsafe(
                    self._run_pings(), self.loop
                )
        else:
            if self.pinger_coroutine is not None:
                self.pinger_coroutine.cancel()
                self.pinger_coroutine = None
