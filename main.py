"""Main entry point for the PingBar application.

This module contains the main function that starts the PingBar macOS menu bar
application for monitoring network connectivity status.
"""

from rumps import debug_mode as rumps_debug_mode

from app import PingBarApp

rumps_debug_mode(True)

def main() -> None:
    """Main entry point for the PingBar application.
    
    Initializes and starts the PingBar macOS menu bar application.
    The application will run until the user quits it.
    """
    pingbar_app = PingBarApp("PingBar")
    pingbar_app.run()

if __name__ == "__main__":
    main()