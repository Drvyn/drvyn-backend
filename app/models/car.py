from pydantic import BaseModel
from typing import List, Optional

class CarModel(BaseModel):
    name: str
    imageUrl: Optional[str] = None
    fuel_types: List[str] = []

class CarBrand(BaseModel):
    brand: str
    logoUrl: Optional[str] = None
    models: List[CarModel] = []

class CarRequest(BaseModel):
    brand: str
    model: str
    fuelType: str
    year: str
    phone: str