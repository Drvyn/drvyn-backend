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

# Configure logging
logging.basicConfig(level=logging.INFO)

class ServicePackage(BaseModel):
    name: str
    warranty: str
    interval: str
    services: List[str]
    duration: str
    recommended: Optional[bool] = False
    category: Optional[str] = None
    pricing: dict
    Extra: Optional[str] = None  
    Extra1: Optional[str] = None 


@router.get("/service-packages")
def get_service_packages(
    category: str = Query(...),
    fuel_type: str = Query("Petrol"),
    brand: str = Query(""),
    model: str = Query("")
):
    try:
        # Decode the URL-encoded category
        decoded_category = unquote(category)
        
        # Validate inputs
        valid_fuels = ["Petrol", "Diesel", "CNG", "Electric", "Hybrid"]
        if fuel_type not in valid_fuels:
            return JSONResponse(
                status_code=400,
                content={"message": f"Invalid fuel type. Must be one of {', '.join(valid_fuels)}"}
            )
            
        if not brand or not model:
            return JSONResponse(
                status_code=400,
                content={"message": "Brand and model are required"}
            )
            
        # OPTIMIZED QUERY:
        # 1. Filter by Category
        # 2. Check if the specific Brand -> Model exists in the pricing object
        query = {
            "category": {"$regex": f"^{decoded_category}$", "$options": "i"},
            f"pricing.brands.{brand}.models.{model}": {"$exists": True}
        }
        
        # PROJECTION:
        # Fetch only the fields we need. We don't need the entire pricing table for every car.
        projection = {
            "name": 1,
            "warranty": 1,
            "interval": 1,
            "services": 1,
            "duration": 1,
            "recommended": 1,
            "category": 1,
            "pricing": 1, # We still fetch pricing, but we filtered the docs already
            "Extra": 1,
            "Extra1": 1
        }
        
        logger.info(f"Executing optimized query for {decoded_category}, {brand}, {model}")
        
        # Executing Sync Query (No 'await')
        packages = list(db.service_packages.find(query, projection))
        
        transformed_packages = []
        for pkg in packages:
            try:
                # We know the path exists because of the query, but we use safe getters just in case
                # Note: We must case-insensitive match or assume DB has exact casing. 
                # The query above assumes exact casing for keys in dictionary.
                
                # Navigate deep into the nested structure
                brand_data = pkg.get("pricing", {}).get("brands", {}).get(brand, {})
                model_data = brand_data.get("models", {}).get(model, {})
                fuel_data = model_data.get("fuelTypes", {}).get(fuel_type)
                
                if not fuel_data:
                    # Package exists for model, but not for this specific fuel type
                    continue
                
                price = fuel_data.get("basePrice", 0)
                discounted_price = fuel_data.get("discountedPrice", price)
                
                # Flatten the structure for the frontend
                transformed = {
                    "name": pkg.get("name"),
                    "warranty": pkg.get("warranty"),
                    "interval": pkg.get("interval"),
                    "services": pkg.get("services"),
                    "duration": pkg.get("duration"),
                    "recommended": pkg.get("recommended"),
                    "category": pkg.get("category"),
                    "price": price,
                    "discountedPrice": discounted_price,
                    "Extra": fuel_data.get("Extra", pkg.get("Extra", "")),
                    "Extra1": fuel_data.get("Extra1", pkg.get("Extra1", "")) 
                }
                transformed_packages.append(transformed)
                
            except (KeyError, TypeError) as e:
                logger.error(f"Error processing package {pkg.get('name')}: {e}")
                continue
            
        return transformed_packages
        
    except Exception as e:
        logger.error(f"Error getting packages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/service-packages")
def create_service_package(package: ServicePackage):
    try:
        package_data = package.dict()
        if not package_data.get("pricing", {}).get("brands", {}):
            raise HTTPException(status_code=400, detail="Pricing must include at least one brand")
        
        result = db.service_packages.insert_one(package_data)
        return {"id": str(result.inserted_id), "message": "Package created successfully"}
    except Exception as e:
        logger.error(f"Error creating package: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/service-packages/{package_name}")
def update_service_package(package_name: str, package: ServicePackage):
    try:
        package_data = package.dict()
        result = db.service_packages.update_one(
            {"name": package_name},
            {"$set": package_data}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Package not found")
        return {"message": "Package updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))