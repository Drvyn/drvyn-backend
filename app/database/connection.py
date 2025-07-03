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
            tlsAllowInvalidCertificates=False,  # Explicitly set to False for security
            connectTimeoutMS=10000,  # Increased connection timeout
            socketTimeoutMS=30000,   # Increased socket timeout
            retryWrites=True,
            w="majority"
        )
        
        # Test connection with a shorter timeout
        client.admin.command('ping', socketTimeoutMS=2000)
        logger.info("✅ MongoDB connection successful!")
        return client[settings.DB_NAME]
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        raise

# Initialize connection
db = get_db_connection()