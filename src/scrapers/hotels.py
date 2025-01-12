from pydantic import BaseModel, Field
from typing import Optional, Dict

class Listing(BaseModel):
    """Pydantic model for Airbnb listing data"""
    name: str = Field(description="The name/title of the listing")
    price: float = Field(description="The price per night")
    rating: float = Field(description="The rating score")
    bed_configuration: Optional[str] = Field(description="Bed configuration details", default=None)

    @classmethod
    def get_json_schema(cls) -> Dict:
        """Get the JSON schema for Gemini API"""
        return {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The name/title of the listing"},
                    "price": {"type": "number", "description": "The price per night"},
                    "rating": {"type": "number", "description": "The rating score"},
                    "bed_configuration": {"type": "string", "description": "Bed configuration details"}
                },
                "required": ["name", "price", "rating"]
            }
        }
