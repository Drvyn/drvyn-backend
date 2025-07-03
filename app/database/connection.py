from pymongo import MongoClient
from app.config import settings
import logging
import certifi

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Create and return a secure MongoDB connection"""
    try:
        client = MongoClient(
            settings.MONGODB_URI,
            tls=True,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=5000,
            retryWrites=True,
            w="majority"
        )
        
        # Test connection
        client.admin.command('ping')
        logger.info("✅ MongoDB connection successful!")
        return client[settings.DB_NAME]
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        raise

# Initialize connection
db = get_db_connection()