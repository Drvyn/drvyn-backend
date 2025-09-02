from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import jwt
from bson import ObjectId
import bcrypt
from app.database.connection import db
import os

router = APIRouter()
security = HTTPBearer()

# JWT Secret
SECRET_KEY = os.getenv("JWT_SECRET", "6ebab7e3a4604d8a350a8510f7a806f0")
ALGORITHM = "HS256"

class AdminLogin(BaseModel):
    username: str
    password: str

class StatusUpdate(BaseModel):
    status: str

# Create admin user if not exists
def create_initial_admin():
    try:
        admin_exists = db.admin_users.find_one({"username": "admin"})
        if not admin_exists:
            hashed_password = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt())
            db.admin_users.insert_one({
                "username": "admin",
                "password": hashed_password,
                "role": "admin",
                "createdAt": datetime.now()
            })
    except Exception as e:
        print(f"Error creating admin user: {e}")

create_initial_admin()

def verify_password(plain_password, hashed_password):
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password)
    except:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
        admin = db.admin_users.find_one({"username": username})
        if admin is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
        return admin
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

@router.post("/login")
async def login(admin_login: AdminLogin):
    try:
        admin = db.admin_users.find_one({"username": admin_login.username})
        if not admin or not verify_password(admin_login.password, admin["password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )
        
        access_token = create_access_token(data={"sub": admin_login.username})
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bookings")
async def get_all_bookings(
    skip: int = 0, 
    limit: int = 50,
    status_filter: Optional[str] = None,
):
    query = {}
    if status_filter:
        query["status"] = status_filter
        
    bookings = list(db.bookings.find(query).sort("createdAt", -1).skip(skip).limit(limit))
    total = db.bookings.count_documents(query)
    
    for booking in bookings:
        booking["_id"] = str(booking["_id"])
        
    return {"bookings": bookings, "total": total}

@router.get("/bookings/{booking_id}")
async def get_booking(booking_id: str, current_admin: dict = Depends(get_current_admin)):
    try:
        booking = db.bookings.find_one({"_id": ObjectId(booking_id)})
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
            
        booking["_id"] = str(booking["_id"])
        return booking
    except:
        raise HTTPException(status_code=400, detail="Invalid booking ID")

@router.put("/bookings/{booking_id}/status")
async def update_booking_status(
    booking_id: str, 
    status_update: StatusUpdate,
):
    try:
        result = db.bookings.update_one(
            {"_id": ObjectId(booking_id)},
            {"$set": {"status": status_update.status, "updatedAt": datetime.now()}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Booking not found")
            
        return {"message": "Status updated successfully"}
    except:
        raise HTTPException(status_code=400, detail="Invalid booking ID")

@router.get("/insurance-requests")
async def get_insurance_requests(
    skip: int = 0, 
    limit: int = 50,
    status_filter: Optional[str] = None,
    current_admin: dict = Depends(get_current_admin)
):
    query = {"type": "insurance_request"}
    if status_filter:
        query["status"] = status_filter
        
    requests = list(db.insurance_requests.find(query).sort("createdAt", -1).skip(skip).limit(limit))
    total = db.insurance_requests.count_documents(query)
    
    for req in requests:
        req["_id"] = str(req["_id"])
        
    return {"requests": requests, "total": total}

@router.put("/insurance-requests/{request_id}/status")
async def update_insurance_request_status(
    request_id: str, 
    status_update: StatusUpdate,
    current_admin: dict = Depends(get_current_admin)
):
    try:
        result = db.insurance_requests.update_one(
            {"_id": ObjectId(request_id)},
            {"$set": {"status": status_update.status, "updatedAt": datetime.now()}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Insurance request not found")
            
        return {"message": "Status updated successfully"}
    except:
        raise HTTPException(status_code=400, detail="Invalid insurance request ID")

@router.get("/car-requests")
async def get_car_requests(
    skip: int = 0, 
    limit: int = 50,
    current_admin: dict = Depends(get_current_admin)
):
    query = {}
        
    requests = list(db.requests.find(query).sort("createdAt", -1).skip(skip).limit(limit))
    total = db.requests.count_documents(query)
    
    for req in requests:
        req["_id"] = str(req["_id"])
        
    return {"requests": requests, "total": total}

@router.get("/dashboard/stats")
async def get_dashboard_stats(current_admin: dict = Depends(get_current_admin)):
    total_bookings = db.bookings.count_documents({})
    pending_bookings = db.bookings.count_documents({"status": "pending"})
    completed_bookings = db.bookings.count_documents({"status": "completed"})
    
    # Calculate revenue (sum of all completed bookings)
    pipeline = [
        {"$match": {"status": "completed"}},
        {"$group": {"_id": None, "totalRevenue": {"$sum": "$totalPrice"}}}
    ]
    revenue_result = list(db.bookings.aggregate(pipeline))
    total_revenue = revenue_result[0]["totalRevenue"] if revenue_result else 0
    
    # Insurance requests
    total_insurance_requests = db.insurance_requests.count_documents({"type": "insurance_request"})
    pending_insurance_requests = db.insurance_requests.count_documents({"type": "insurance_request", "status": "new"})
    
    # Car requests
    total_car_requests = db.requests.count_documents({})
    
    return {
        "totalBookings": total_bookings,
        "pendingBookings": pending_bookings,
        "completedBookings": completed_bookings,
        "totalRevenue": total_revenue,
        "totalInsuranceRequests": total_insurance_requests,
        "pendingInsuranceRequests": pending_insurance_requests,
        "totalCarRequests": total_car_requests
    }