from typing import Dict, Any
from pydantic import BaseModel, Field, RootModel


class Evaluator(BaseModel):
    should_google: bool = Field(
        description="Set to 'True' ONLY if NO relevant data is found in the API results, and 'False' if any relevant data is present."
    )
    is_high_occupancy: bool = Field(
        description="Set to 'True' if most of the results indicate high occupancy or full capacity, especially for shelters and 'False' otherwise."
    )


class ContactInfo(BaseModel):
    address: str = Field(
        description="The address of the resource. Perferably in the format: '[Name of location] - [Address]'."
    )
    phone: str = Field(
        description="The phone number available for the resource. Leave empty if not available."
    )
    email: str = Field(
        description="The email address available for the resource. Leave empty if not available."
    )
    website: str = Field(
        description="The website available for the resource. Leave empty if not available."
    )


class AgentResponse(BaseModel):
    addresses: list[ContactInfo] = Field(
        description="List of contact information for the requested resources. Leave empty if not available."
    )
    feedback: str = Field(description="Extra information about the resources gathered.")
