"""Pydantic models for PingrThingr application settings validation.

Provides data models and validation functions for application configuration,
including IP address validation and settings schema definition.
"""

import logging

logger = logging.getLogger(__name__)

from pydantic import BaseModel, ConfigDict, Field, AfterValidator, model_validator
from socket import inet_aton
from typing import Annotated, Literal


def validate_ip_address(value):
    """Validate that a string represents a valid IPv4 address.
    
    Uses socket.inet_aton to verify the IP address format. This function
    is used as a Pydantic validator for IP address fields.
    
    Args:
        value (str): The IP address string to validate.
        
    Returns:
        str: The validated IP address string if valid.
        
    Raises:
        ValueError: If the IP address format is invalid.
    """
    try:
        inet_aton(value)
        return value
    except OSError as e:
        raise ValueError(f"Invalid IP address: {value}") from e


IPAddress = Annotated[str, AfterValidator(validate_ip_address)]
IconStyle = Literal["Dot", "Text"]

class ThresholdModel(BaseModel):
    """Pydantic model for threshold configuration values.
    
    Defines threshold values for warning, alert, and critical states
    used in network status evaluation.
    
    Attributes:
        warn (float): Threshold value for warning state.
        alert (float): Threshold value for alert state.
        critical (float): Threshold value for critical state.
    """
    warn: float = Field(description="Threshold for warning state")
    alert: float = Field(description="Threshold for error state ")
    critical: float = Field(description="Threshold for critical state")

class SettingsModel(BaseModel):
    """Pydantic model for PingrThingr application settings.
    
    Defines the schema and validation rules for application configuration
    settings including display mode, pause state, and ping targets.
    
    Attributes:
        display_mode (Literal["Dot", "Text"]): Status icon display mode.
        paused (bool): Whether the application is currently paused.
        targets (list[IPAddress]): List of target IP addresses to ping.
    """
    model_config = ConfigDict(validate_assignment=True)

    display_mode: IconStyle = Field(
        default="Dot", description=f"Display mode for status icon (one of {', '.join(IconStyle.__args__)})"
    )
    paused: bool = Field(default=False, description="Whether the application is paused")
    targets: list[IPAddress] = Field(
        default=["8.8.8.8", "8.8.4.4", "1.1.1.1", "1.0.0.1"],
        description="List of target IP addresses to ping",
    )
    latency_thresholds: ThresholdModel = Field(
        default=ThresholdModel(warn=80.0, alert=500.0, critical=1000.0),
        description="Latency thresholds for warning, alert, and critical states",
    )
    loss_thresholds: ThresholdModel = Field(
        default=ThresholdModel(warn=0.0, alert=0.05, critical=0.25),
        description="Packet loss thresholds for warning, alert, and critical states",
    )

    @model_validator(mode="before")
    @classmethod
    def log_defaults(cls, data):
        """Log when default values are being used for missing fields.
        
        This validator runs before field validation to log informational
        messages when configuration fields are not provided and defaults
        will be used instead. Helps with debugging configuration issues.
        
        Args:
            data (dict): The input configuration data dictionary.
            
        Returns:
            dict: The unmodified input data dictionary.
        """
        if isinstance(data, dict):  # pragma: no branch
            # Check fields that have defaults defined in the model
            for field_name, field_info in cls.model_fields.items():
                if field_info.default is not None and field_name not in data:
                    logging.info(
                        f"Field '{field_name}' not provided; using default value"
                    )
        return data
