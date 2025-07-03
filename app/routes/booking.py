# booking.py
from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import Dict, List
from pydantic import BaseModel
import logging
from bson import ObjectId
from app.database.connection import db 

router = APIRouter()
logger = logging.getLogger(__name__)

class BookingItem(BaseModel):
    packageName: str
    price: float
    quantity: int

class BookingRequest(BaseModel):
    brand: str
    model: str
    fuelType: str
    year: str
    phone: str
    date: str
    time: str
    address: str
    alternatePhone: str = ""
    serviceCenter: str
    totalPrice: float
    cartItems: List[BookingItem]
    status: str = "pending"  # Default status
    
@router.post("/submit-booking")
async def submit_booking(booking: BookingRequest):
    try:
        logger.info(f"Received booking data: {booking.dict()}")
        
        if db is None:
            logger.error("Database connection not initialized")
            raise HTTPException(status_code=500, detail="Database connection error")
            
        booking_data = booking.dict()
        booking_data["createdAt"] = datetime.utcnow()
        booking_data["updatedAt"] = datetime.utcnow()
        
        # Insert the booking into MongoDB
        result = db.bookings.insert_one(booking_data)
        
        return {
            "success": True,
            "bookingId": str(result.inserted_id),
            "message": "Booking submitted successfully"
        }
        
    except Exception as e:
        logger.error(f"Error submitting booking: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bookings")
async def get_bookings(phone: str = None):
    try:
        query = {}
        if phone:
            query["phone"] = phone
            
        bookings = list(db.bookings.find(query).sort("createdAt", -1))
        
        # Convert ObjectId to string for JSON serialization
        for booking in bookings:
            booking["_id"] = str(booking["_id"])
            
        return bookings
        
    except Exception as e:
        logger.error(f"Error fetching bookings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))