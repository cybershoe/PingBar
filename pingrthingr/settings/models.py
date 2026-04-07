import logging

logger = logging.getLogger(__name__)

from pydantic import BaseModel, Field, AfterValidator
from socket import inet_aton
from typing import Annotated, Literal


def validate_ip_address(value):
    try:
        inet_aton(value)
        return value
    except OSError as e:
        raise ValueError(f"Invalid IP address: {value}") from e
    
IPAddress = Annotated[str, AfterValidator(validate_ip_address)]

class SettingsModel(BaseModel):
    display_mode: Literal['Dot', 'Text'] = Field(default="Dot", description="Display mode for status icon (Dot or Text)")
    paused: bool = Field(default=False, description="Whether the application is paused")
    ping_targets: list[IPAddress] = Field(default_factory=list, description="List of target IP addresses to ping")

