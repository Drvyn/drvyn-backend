from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from app.database.connection import db
from app.models.car import CarBrand, CarRequest
from app.config import settings
from typing import List
import os
import shutil
from datetime import datetime
from pathlib import Path
import logging
import re
import pytz

router = APIRouter()
logger = logging.getLogger(__name__)

# Define IST time zone
IST_TZ = pytz.timezone('Asia/Kolkata')

def normalize_name(name: str) -> str:
    """Convert to lowercase and replace spaces with underscores"""
    return re.sub(r'\s+', '_', name.lower().strip())

def save_uploaded_file(file: UploadFile, category: str, name: str) -> dict:
    try:
        # Normalize name and create directory
        normalized_name = normalize_name(name)
        category_dir = settings.MEDIA_ROOT / category
        category_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_ext = file.filename.split(".")[-1].lower()
        filename = f"{normalized_name}_{timestamp}.{file_ext}"
        filepath = category_dir / filename
        
        # Save the file
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "filename": filename,
            "url": f"{settings.MEDIA_URL}{category}/{filename}"
        }
    except Exception as e:
        logger.error(f"Error saving file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        file.file.close()

@router.post("/upload-brand-logo")
async def upload_brand_logo(brand: str, file: UploadFile = File(...)):
    result = save_uploaded_file(file, "brands", brand)
    
    # Update or create brand document
    db.brands.update_one(
        {"brand": brand},
        {"$set": {
            "brand": brand,
            "logoUrl": result["url"]
        }},
        upsert=True
    )
    
    return result

@router.post("/upload-model-image")
async def upload_model_image(brand: str, model: str, file: UploadFile = File(...)):
    result = save_uploaded_file(file, "models", f"{brand}_{model}")
    
    # Update model in database
    db.brands.update_one(
        {"brand": brand, "models.name": model},
        {"$set": {"models.$.imageUrl": result["url"]}},
        upsert=True
    )
    
    # If model doesn't exist, add it
    db.brands.update_one(
        {"brand": brand, "models.name": {"$ne": model}},
        {"$push": {"models": {
            "name": model,
            "imageUrl": result["url"],
            "fuel_types": []
        }}},
        upsert=True
    )
    
    return result

@router.post("/add-fuel-type")
async def add_fuel_type(brand: str, model: str, fuel_type: str):
    # Normalize fuel type
    normalized_fuel = fuel_type.strip().capitalize()
    
    db.brands.update_one(
        {"brand": brand, "models.name": model},
        {"$addToSet": {"models.$.fuel_types": normalized_fuel}},
        upsert=True
    )
    
    return {"message": f"Fuel type {normalized_fuel} added to {brand} {model}"}

# ... (keep other endpoints the same)

@router.get("/brand-logos", response_model=List[dict])
async def get_brand_logos():
    try:
        brands_dir = settings.MEDIA_ROOT / "brands"
        logos = []
        
        if brands_dir.exists():
            for filename in os.listdir(brands_dir):
                if not filename.startswith("."):
                    brand_name = filename.split("_")[0].capitalize()
                    logos.append({
                        "brand": brand_name,
                        "url": f"{settings.MEDIA_URL}brands/{filename}"
                    })
        
        return logos
    except Exception as e:
        logger.error(f"Error getting brand logos: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/model-images/{brand}", response_model=List[dict])
async def get_model_images(brand: str):
    try:
        models_dir = settings.MEDIA_ROOT / "models"
        images = []
        
        if models_dir.exists():
            for filename in os.listdir(models_dir):
                if filename.startswith(f"{brand.lower()}_") and not filename.startswith("."):
                    parts = filename.split("_")
                    model_name = " ".join(part.capitalize() for part in parts[1:-1])
                    images.append({
                        "model": model_name,
                        "url": f"{settings.MEDIA_URL}models/{filename}"
                    })
        
        return images
    except Exception as e:
        logger.error(f"Error getting model images: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/fuel-icons", response_model=List[dict])
async def get_fuel_icons():
    try:
        fuels_dir = settings.MEDIA_ROOT / "fuels"
        icons = []
        
        if fuels_dir.exists():
            for filename in os.listdir(fuels_dir):
                if not filename.startswith("."):
                    fuel_type = filename.split(".")[0].capitalize()
                    icons.append({
                        "type": fuel_type,
                        "url": f"{settings.MEDIA_URL}fuels/{filename}"
                    })
        
        return icons
    except Exception as e:
        logger.error(f"Error getting fuel icons: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/all-brands", response_model=List[CarBrand])
async def get_all_brands():
    try:
        brands = list(db.brands.find({}))
        return brands
    except Exception as e:
        logger.error(f"Error getting all brands: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import Response

@router.post("/submit-request")
async def submit_request(request: CarRequest, response: Response):
    try:
        request_data = {
            "brand": request.brand,
            "model": request.model,
            "fuelType": request.fuelType,
            "year": request.year,
            "phone": request.phone,
            "createdAt": datetime.now(IST_TZ).strftime("%Y-%m-%d %H:%M:%S")  

        }
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "POST"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        
        result = db.requests.insert_one(request_data)
        return {
            "message": "Request submitted successfully",
            "id": str(result.inserted_id)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
