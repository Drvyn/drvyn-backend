from dotenv import load_dotenv
from pathlib import Path
import os

# Load environment variables
load_dotenv()

# Database settings - no default values for security
MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise ValueError("MONGODB_URI environment variable not set")

DB_NAME = os.getenv("DB_NAME", "carbrands")  # Default okay for DB_NAME

# Media settings
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

class Settings:
    MONGODB_URI = MONGODB_URI
    DB_NAME = DB_NAME
    MEDIA_ROOT = MEDIA_ROOT
    MEDIA_URL = MEDIA_URL

settings = Settings()
