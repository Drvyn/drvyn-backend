from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.routes.car import router as car_router
from app.config import settings
from app.routes.service import router as service_router
from app.routes.booking import router as booking_router
from fastapi import BackgroundTasks
import httpx
import asyncio
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.drvyn.in",
        "https://drvyn-frontend.vercel.app  ",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "https://drvyn-backend.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Create media directories if they don't exist
os.makedirs(settings.MEDIA_ROOT / "brands", exist_ok=True)
os.makedirs(settings.MEDIA_ROOT / "models", exist_ok=True)
os.makedirs(settings.MEDIA_ROOT / "fuels", exist_ok=True)

# Serve static files
app.mount(
    str(settings.MEDIA_URL),
    StaticFiles(directory=settings.MEDIA_ROOT),
    name="media"
)

async def keep_alive():
    while True:
        try:
            async with httpx.AsyncClient() as client:
                await client.get("https://drvyn-backend.onrender.com")
            logger.info("Keep-alive ping successful")
        except Exception as e:
            logger.error(f"Keep-alive ping failed: {e}")
        await asyncio.sleep(60)  # Ping every # minutes

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(keep_alive())

# Include routes
app.include_router(car_router, prefix="/car", tags=["Car"])
app.include_router(service_router, prefix="/api")
app.include_router(booking_router, prefix="/api", tags=["Booking"]) 

@app.get("/")
def root():
    return {"status": "API is running"}

logger.info(f"📁 Media root: {settings.MEDIA_ROOT}")
logger.info(f"🌐 Media URL: {settings.MEDIA_URL}")

app.include_router(service_router)
@app.get("/")
def read_root():
    return {"message": "Service Hierarchy API is running"}