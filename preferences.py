from rumps import Window, alert
from typing import List
from socket import inet_aton

def getPreferences(targets: List[str]) -> List[str]:
    while True:
        response = Window(
            title="Ping Targets",
            message="Enter target IP addresses (comma-separated):",
            default_text=",".join(targets),
            dimensions=(300, 24),
            cancel="Cancel",
            ok="Save",
        ).run()

        if response.clicked == 1:
            new_targets = [t.strip() for t in response.text.split(",") if t.strip()]
            try:
                for target in new_targets:
                    inet_aton(target)
            except OSError:
                alert(f"Invalid IP address: {target}")
                print(targets)
            else:
                return new_targets
        else:
            return None
