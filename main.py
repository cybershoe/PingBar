"""Main entry point for the PingBar application.

This module contains the main function that starts the PingBar macOS menu bar
application for monitoring network connectivity status.
"""
import logging
from os import environ

LOGLEVEL = environ.get('LOGLEVEL', 'WARN').upper()  
logging.basicConfig(
    level=LOGLEVEL
)
logger = logging.getLogger(__name__)

if logger.getEffectiveLevel() <= logging.DEBUG:
    from rumps import debug_mode as rumps_debug_mode
    rumps_debug_mode(True)

from app import PingBarApp


def main() -> None:
    """Main entry point for the PingBar application.
    
    Initializes and starts the PingBar macOS menu bar application.
    The application will run in the system menu bar and monitor network
    connectivity until the user quits it through the menu interface.
    
    Returns:
        None
    """
    pingbar_app = PingBarApp("PingBar")
    pingbar_app.run()

if __name__ == "__main__":
    main()