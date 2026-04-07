import logging

logger = logging.getLogger(__name__)

from pydantic import BaseModel, ConfigDict, Field, AfterValidator, model_validator
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
    model_config = ConfigDict(validate_assignment=True)

    display_mode: Literal['Dot', 'Text'] = Field(default="Dot", description="Display mode for status icon (Dot or Text)")
    paused: bool = Field(default=False, description="Whether the application is paused")
    targets: list[IPAddress] = Field(default_factory=list, description="List of target IP addresses to ping")

    @model_validator(mode='before')
    @classmethod
    def log_defaults(cls, data):
        if isinstance(data, dict):
            # Check fields that have defaults defined in the model
            for field_name, field_info in cls.model_fields.items():
                if field_info.default is not None and field_name not in data:
                    logging.info(f"Field '{field_name}' not provided; using default value")
        return data
