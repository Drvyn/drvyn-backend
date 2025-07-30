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
    Extra: Optional[dict] = None

@router.get("/service-packages")
async def get_service_packages(
    category: str = Query(...),
    fuel_type: str = Query("Petrol"),
    brand: str = Query(""),
    model: str = Query("")
):
    try:
        # Decode the URL-encoded category
        decoded_category = unquote(category)
        logger.info(f"Received request: category={decoded_category}, fuel_type={fuel_type}, brand={brand}, model={model}")
        
        # Validate inputs
        valid_fuels = ["Petrol", "Diesel", "CNG", "Electric", "Hybrid"]
        if fuel_type not in valid_fuels:
            logger.warning(f"Invalid fuel type: {fuel_type}")
            return JSONResponse(
                status_code=400,
                content={"message": f"Invalid fuel type. Must be one of {', '.join(valid_fuels)}"}
            )
            
        if not brand or not model:
            logger.warning("Brand and model are required")
            return JSONResponse(
                status_code=400,
                content={"message": "Brand and model are required"}
            )
            
        # Build query with case-insensitive matching
        query = {"category": {"$regex": f"^{decoded_category}$", "$options": "i"}}
        logger.info(f"Executing query: {query}")
        
        # Fetch packages
        packages = list(db.service_packages.find(query, {"_id": 0}))
        logger.info(f"Found {len(packages)} packages matching category")
        
        if not packages:
            logger.warning(f"No packages found for category: {decoded_category}")
            return JSONResponse(
                status_code=404,
                content={"message": f"No packages found for category: {decoded_category}"}
            )
            
        # Transform packages to include only those with pricing for the specified brand and model
        transformed_packages = []
        for pkg in packages:
            try:
                # Case-insensitive lookup for brand and model
                brand_lower = brand.lower()
                model_lower = model.lower()
                
                brands = pkg.get("pricing", {}).get("brands", {})
                brand_data = next((v for k, v in brands.items() if k.lower() == brand_lower), None)
                
                if not brand_data:
                    logger.debug(f"Brand {brand} not found in package: {pkg['name']}")
                    continue
                
                models = brand_data.get("models", {})
                model_data = next((v for k, v in models.items() if k.lower() == model_lower), None)
                
                if not model_data:
                    logger.debug(f"Model {model} not found in package: {pkg['name']}")
                    continue
                
                fuel_data = model_data.get("fuelTypes", {}).get(fuel_type)
                if not fuel_data:
                    logger.debug(f"Fuel type {fuel_type} not found in package: {pkg['name']}")
                    continue
                
                price = fuel_data.get("basePrice", 0)
                discounted_price = fuel_data.get("discountedPrice", price)
                
                transformed = {
                    **pkg,
                    "price": price,
                    "discountedPrice": discounted_price,
                    "Extra": fuel_data.get("Extra", "") 
                }
                transformed_packages.append(transformed)
                logger.info(f"Included package: {pkg['name']} for {brand} {model} ({fuel_type})")
            except (KeyError, TypeError) as e:
                logger.debug(f"Error processing package {pkg.get('name', 'unknown')}: {str(e)}")
                continue
            
        if not transformed_packages:
            logger.warning(f"No packages found for {brand} {model} ({fuel_type}) in category: {decoded_category}")
            return JSONResponse(
                status_code=404,
                content={"message": f"No packages found for {brand} {model} ({fuel_type}) in category: {decoded_category}"}
            )
            
        logger.info(f"Returning {len(transformed_packages)} packages")
        return transformed_packages
        
    except Exception as e:
        logger.error(f"Error getting packages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/service-packages")
async def create_service_package(package: ServicePackage):
    try:
        package_data = package.dict()
        
        # Validate pricing structure
        pricing = package_data.get("pricing", {}).get("brands", {})
        if not pricing:
            logger.warning("Invalid pricing structure: no brands provided")
            raise HTTPException(
                status_code=400,
                detail="Pricing must include at least one brand with models and fuel types"
            )
        
        result = db.service_packages.insert_one(package_data)
        logger.info(f"Created package: {package_data['name']} with ID: {result.inserted_id}")
        return {"id": str(result.inserted_id), "message": "Package created successfully"}
    except Exception as e:
        logger.error(f"Error creating package: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/service-packages/{package_name}")
async def update_service_package(package_name: str, package: ServicePackage):
    try:
        package_data = package.dict()
        
        # Validate pricing structure
        pricing = package_data.get("pricing", {}).get("brands", {})
        if not pricing:
            logger.warning("Invalid pricing structure: no brands provided")
            raise HTTPException(
                status_code=400,
                detail="Pricing must include at least one brand with models and fuel types"
            )
        
        result = db.service_packages.update_one(
            {"name": package_name},
            {"$set": package_data}
        )
        if result.modified_count == 0:
            logger.warning(f"Package not found: {package_name}")
            raise HTTPException(status_code=404, detail="Package not found")
        logger.info(f"Updated package: {package_name}")
        return {"message": "Package updated successfully"}
    except Exception as e:
        logger.error(f"Error updating package: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))