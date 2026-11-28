import sqlite3
import json
import os
import redis

# Redis connection for caching
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

try:
    redis_client = redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1)
    redis_client.ping()  # Test connection
    REDIS_AVAILABLE = True
except Exception as e:
    print(f"Redis not available for caching: {e}. Running without cache.")
    redis_client = None
    REDIS_AVAILABLE = False

CACHE_TTL = 300  # 5 minutes

DB_PATH = os.getenv(
    "DATABASE_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'complaints.db')
)

# Ensure the database directory exists (matters when DATABASE_PATH points at a
# Render persistent disk mount or a custom folder on Windows).
_db_dir = os.path.dirname(os.path.abspath(DB_PATH))
if _db_dir and not os.path.exists(_db_dir):
    os.makedirs(_db_dir, exist_ok=True)


def get_db_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS complaints(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        registered_on TEXT,
        english_name TEXT,
        telugu_name TEXT,
        phone TEXT,
        subject TEXT,
        audio_path TEXT,
        telugu_complaint TEXT,
        english_complaint TEXT
    )
    """)
    conn.commit()
    conn.close()


def save_complaint(
    registered_on,
    english_name,
    telugu_name,
    phone,
    subject,
    audio_path,
    telugu_complaint,
    english_complaint
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO complaints(
            registered_on,
            english_name,
            telugu_name,
            phone,
            subject,
            audio_path,
            telugu_complaint,
            english_complaint
        )
        VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            registered_on,
            english_name,
            telugu_name,
            phone,
            subject,
            audio_path,
            telugu_complaint,
            english_complaint
        )
    )
    complaint_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # Invalidate cache after write
    invalidate_complaint_cache()

    return complaint_id


def get_complaints():
    """Get all complaints with Redis caching."""
    cache_key = "complaints:all"
    if REDIS_AVAILABLE and redis_client:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM complaints ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    # Cache the result
    if REDIS_AVAILABLE and redis_client:
        redis_client.setex(cache_key, CACHE_TTL, json.dumps(rows))
    return rows


def get_complaint_by_id(complaint_id):
    """Get a single complaint by ID with Redis caching."""
    cache_key = f"complaint:{complaint_id}"
    if REDIS_AVAILABLE and redis_client:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM complaints WHERE id=?", (complaint_id,))
    row = cursor.fetchone()
    conn.close()

    if row and REDIS_AVAILABLE and redis_client:
        # Cache the result
        redis_client.setex(cache_key, CACHE_TTL, json.dumps(row))

    return row


def update_audio_path(complaint_id, audio_path):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE complaints
        SET audio_path = ?
        WHERE id = ?
        """,
        (audio_path, complaint_id)
    )
    conn.commit()
    conn.close()

    # Invalidate cache after write
    invalidate_complaint_cache(complaint_id)


def invalidate_complaint_cache(complaint_id=None):
    """Invalidate complaint cache after write operations."""
    if not REDIS_AVAILABLE or not redis_client:
        return
    if complaint_id:
        redis_client.delete(f"complaint:{complaint_id}")
    redis_client.delete("complaints:all")
    redis_client.delete("complaints:statistics")


def get_statistics():
    """Get statistics with Redis caching."""
    cache_key = "complaints:statistics"
    if REDIS_AVAILABLE and redis_client:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)

    from datetime import datetime
    conn = get_db_connection()
    cursor = conn.cursor()

    # Total complaints
    cursor.execute("SELECT COUNT(*) FROM complaints")
    total_cases = cursor.fetchone()[0]

    today = datetime.now().strftime("%d-%m-%Y")
    # Today's complaints
    cursor.execute(
        "SELECT COUNT(*) FROM complaints WHERE registered_on LIKE ?",
        (f"{today}%",)
    )
    today_cases = cursor.fetchone()[0]

    current_month = datetime.now().strftime("%m-%Y")
    cursor.execute(
        "SELECT COUNT(*) FROM complaints WHERE registered_on LIKE ?",
        (f"%-{current_month}%",)
    )
    month_cases = cursor.fetchone()[0]

    conn.close()

    result = (total_cases, today_cases, month_cases)
    if REDIS_AVAILABLE and redis_client:
        redis_client.setex(cache_key, CACHE_TTL, json.dumps(result))
    return result