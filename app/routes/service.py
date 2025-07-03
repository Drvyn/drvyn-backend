from fastapi import APIRouter, HTTPException, Query, Body
from app.database.connection import db
from fastapi.responses import JSONResponse
from bson import ObjectId
import logging
from typing import Optional, List
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)

class ServicePackage(BaseModel):
    name: str
    price: float
    discountedPrice: float
    warranty: str
    interval: str
    services: List[str]
    duration: str
    recommended: Optional[bool] = False

@router.get("/service-categories")
async def get_service_categories():
    try:
        categories = list(db.service_categories.find({}, {"_id": 0, "name": 1, "icon": 1}))
        return categories
    except Exception as e:
        logger.error(f"Error getting categories: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

from urllib.parse import unquote

@router.get("/service-packages")
async def get_service_packages(category: str = Query(...)):
    try:
        # Decode the URL-encoded category (handles %26 -> &)
        decoded_category = unquote(category)
        packages = list(db.service_packages.find(
            {"category": {"$regex": f"^{decoded_category}$", "$options": "i"}},
            {"_id": 0}
        ))
        
        if not packages:
            return JSONResponse(
                status_code=404,
                content={"message": f"No packages found for category: {decoded_category}"}
            )
            
        return packages
    except Exception as e:
        logger.error(f"Error getting packages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/service-packages")
async def create_service_package(package: ServicePackage):
    try:
        result = db.service_packages.insert_one(package.dict())
        return {"id": str(result.inserted_id), "message": "Package created successfully"}
    except Exception as e:
        logger.error(f"Error creating package: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/service-packages/{package_name}")
async def update_service_package(package_name: str, package: ServicePackage):
    try:
        result = db.service_packages.update_one(
            {"name": package_name},
            {"$set": package.dict()}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Package not found")
        return {"message": "Package updated successfully"}
    except Exception as e:
        logger.error(f"Error updating package: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))