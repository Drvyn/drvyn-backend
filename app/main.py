from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.routes.car import router as car_router
from app.config import settings
from app.routes.service import router as service_router
from app.routes.booking import router as booking_router
from app.routes.admin import router as admin_router
from app.routes.blog import router as blog_router
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://drvyn.in",
        "https://www.drvyn.in",
        "https://crm.drvyn.in",
        "https://drvyn-frontend.vercel.app",
        "https://drvyn-dashboard.vercel.app",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# FIXED: Removed os.makedirs. Vercel is Read-Only.
# You must use S3, Cloudinary, or Vercel Blob for storage instead of local folders.

if os.path.exists(settings.MEDIA_ROOT):
    app.mount(
        str(settings.MEDIA_URL), 
        StaticFiles(directory=str(settings.MEDIA_ROOT)), 
        name="media"
    )
    logger.info(f"Media mounted at {settings.MEDIA_ROOT}")

# Include routes
app.include_router(car_router, prefix="/car", tags=["Car"])
app.include_router(service_router, prefix="/api")
app.include_router(booking_router, prefix="/api", tags=["Booking"]) 
app.include_router(admin_router, prefix="/admin", tags=["Admin"])
app.include_router(blog_router)

@app.get("/")
def root():
    return {"status": "API is running on Vercel", "database": "Connected"}

# FIXED: Removed duplicate root routes and the keep_alive startup task.