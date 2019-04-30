import os


def get_redis_db_url(db: int = 1) -> str:
    host = os.getenv("REDIS_HOST", "localhost")
    port = os.getenv("REDIS_PORT", 6379)
    return f"redis://{host}:{port}/{db}"
