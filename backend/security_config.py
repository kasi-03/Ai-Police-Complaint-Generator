import os
import redis
from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from flask_cors import CORS

# Redis connection with graceful fallback
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

try:
    redis_client = redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1)
    redis_client.ping()  # Test connection
    REDIS_AVAILABLE = True
except Exception as e:
    print(f"Redis not available: {e}. Rate limiting will use in-memory storage.")
    redis_client = None
    REDIS_AVAILABLE = False

# Rate limiter - use Redis if available, otherwise in-memory
if REDIS_AVAILABLE:
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=redis_url,
        default_limits=["200 per day", "50 per hour"],
        storage_options={"socket_connect_timeout": 1, "socket_timeout": 1},
        strategy="fixed-window"
    )
else:
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri="memory://",
        default_limits=["200 per day", "50 per hour"],
        strategy="fixed-window"
    )

# Security headers with Talisman
def init_security_headers(app: Flask):
    """Initialize security headers for the Flask app."""
    Talisman(
        app,
        force_https=not app.debug,
        strict_transport_security=True,
        session_cookie_secure=not app.debug,
        content_security_policy={
            'default-src': "'self'",
            'script-src': "'self' 'unsafe-inline'",
            'style-src': "'self' 'unsafe-inline'",
            'img-src': "'self' data: blob:",
            'font-src': "'self'",
            'connect-src': "'self'",
            'media-src': "'self' blob:",
        },
        referrer_policy='strict-origin-when-cross-origin',
        permissions_policy={
            'microphone': "'self'",
            'camera': "'none'",
            'geolocation': "'none'",
        }
    )

# CORS configuration
def init_cors(app: Flask):
    """Initialize CORS for the Flask app."""
    cors_origins = os.getenv("CORS_ORIGINS", "*")
    if cors_origins == "*":
        CORS(app, supports_credentials=True)
    else:
        origins = [o.strip() for o in cors_origins.split(",")]
        CORS(app, origins=origins, supports_credentials=True)

# Input validation helpers
import re

def validate_phone_number(phone: str) -> bool:
    """Validate Indian phone number format."""
    pattern = r'^[6-9]\d{9}$'
    return bool(re.match(pattern, phone))

def validate_name(name: str) -> bool:
    """Validate name - alphabets, spaces, dots, hyphens only."""
    pattern = r'^[A-Za-z\s.\-]{1,100}$'
    return bool(re.match(pattern, name))

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal."""
    # Remove any directory components
    filename = os.path.basename(filename)
    # Keep only safe characters
    filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
    # Limit length
    return filename[:255]

def validate_audio_file(filename: str) -> bool:
    """Validate audio file extension."""
    allowed_extensions = {'.wav', '.mp3', '.m4a', '.ogg', '.webm', '.aac', '.flac'}
    ext = os.path.splitext(filename)[1].lower()
    return ext in allowed_extensions