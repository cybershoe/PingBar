"""Network pinging functionality for connectivity monitoring.

Provides the core Pinger class that performs periodic network connectivity
checks by sending ICMP ping packets to target IP addresses.
"""

from .pinger import Pinger
