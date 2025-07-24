from fastapi import APIRouter, HTTPException, Query, Body
from app.database.connection import db
from fastapi.responses import JSONResponse
from bson import ObjectId
import logging
from typing import Optional, List
from pydantic import BaseModel
from urllib.parse import unquote

router = APIRouter()
logger = logging.getLogger(__name__)

class ServicePackage(BaseModel):
    name: str
    prices: dict  # Now using dict for fuel-specific prices
    warranty: str
    interval: str
    services: List[str]
    duration: str
    recommended: Optional[bool] = False
    category: Optional[str] = None

@router.get("/service-categories")
async def get_service_categories():
    try:
        categories = list(db.service_categories.find({}, {"_id": 0, "name": 1, "icon": 1}))
        return categories
    except Exception as e:
        logger.error(f"Error getting categories: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/service-packages")
async def get_service_packages(
    category: str = Query(...),
    fuel_type: str = Query("Petrol")  # Default to Petrol if not specified
):
    try:
        # Decode the URL-encoded category
        decoded_category = unquote(category)
        
        # Validate fuel type
        valid_fuels = ["Petrol", "Diesel"]
        if fuel_type not in valid_fuels:
            return JSONResponse(
                status_code=400,
                content={"message": "Invalid fuel type. Must be 'Petrol' or 'Diesel'"}
            )
            
        # Fetch packages and transform to include the selected fuel price
        packages = list(db.service_packages.find(
            {"category": {"$regex": f"^{decoded_category}$", "$options": "i"}},
            {"_id": 0}
        ))
        
        if not packages:
            return JSONResponse(
                status_code=404,
                content={"message": f"No packages found for category: {decoded_category}"}
            )
            
        # Transform packages to include the selected fuel price
        transformed_packages = []
        for pkg in packages:
            # Handle both old (single price) and new (fuel-specific prices) formats
            if "prices" not in pkg:
                # For backward compatibility with old packages
                price = pkg.get("price", 0)
                transformed = {
                    **pkg,
                    "price": price,
                    "discountedPrice": price
                }
            else:
                transformed = {
                    **pkg,
                    "price": pkg["prices"].get("Petrol", 0),  # Default price
                    "discountedPrice": pkg["prices"].get(fuel_type, pkg["prices"].get("Petrol", 0))
                }
            transformed_packages.append(transformed)
            
        return transformed_packages
        
    except Exception as e:
        logger.error(f"Error getting packages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/service-packages")
async def create_service_package(package: ServicePackage):
    try:
        # Convert to dict and handle fuel-specific pricing
        package_data = package.dict()
        if "price" in package_data:
            # Convert single price to fuel-specific pricing
            package_data["prices"] = {
                "Petrol": package_data.pop("price"),
                "Diesel": package_data.pop("price") * 1.15  # Example: Diesel is 15% more
            }
        
        result = db.service_packages.insert_one(package_data)
        return {"id": str(result.inserted_id), "message": "Package created successfully"}
    except Exception as e:
        logger.error(f"Error creating package: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/service-packages/{package_name}")
async def update_service_package(package_name: str, package: ServicePackage):
    try:
        package_data = package.dict()
        if "price" in package_data:
            # Convert single price to fuel-specific pricing
            package_data["prices"] = {
                "Petrol": package_data.pop("price"),
                "Diesel": package_data.pop("price") * 1.15
            }
            
        result = db.service_packages.update_one(
            {"name": package_name},
            {"$set": package_data}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Package not found")
        return {"message": "Package updated successfully"}
    except Exception as e:
        logger.error(f"Error updating package: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))