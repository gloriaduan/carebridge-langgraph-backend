from pydantic import BaseModel, Field, model_validator

class ShelterFilter(BaseModel):
    SECTOR: str = Field(description="The sector of the service (e.g., Families, Mixed Adult, etc.). Empty '' if not stated.")
    OVERNIGHT_SERVICE_TYPE: str = Field(description="The type of overnight service (e.g., Shelter, Motel/Hotel Shelter, etc.). Empty '' if not stated.")
    
    @model_validator(mode="before")
    @classmethod
    def validate_sector_and_service_type(cls, values: dict) -> dict:
        valid_sectors = ["Families", "Mixed Adult", "Men", "Women", "Youth", ""]
        valid_service_types = [
            "Motel/Hotel Shelter", "Shelter", "24-Hour Respite Site",
            "Top Bunk Contingency Space", "Isolation/Recovery Site", "Alternative Space Protocol", ""
        ]

        sector = values.get("SECTOR")
        service_type = values.get("OVERNIGHT_SERVICE_TYPE")

        if sector not in valid_sectors:
            raise ValueError(f"Invalid SECTOR: {sector}. Must be one of {valid_sectors}.")
        if service_type not in valid_service_types:
            raise ValueError(f"Invalid OVERNIGHT_SERVICE_TYPE: {service_type}. Must be one of {valid_service_types}.")

        return values


class ChildrenFamilyCenterFilter(BaseModel):
    french_language_program: str = Field(description="Whether the user query wants the center to offer french language programs. Only 'Yes' or '' are valid.")
    indigenous_program: str = Field(description="Whether the user query wants the center to offer indigenous programs. Only 'Yes' or '' are valid.")
    languages: str = Field(description="The languages spoken at the center. Please provide a semi-colon seperated list of languages. Leave empty if the language is English or not stated.")