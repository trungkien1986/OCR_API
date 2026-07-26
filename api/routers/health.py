import redis
from fastapi import APIRouter, Response, status
from sqlalchemy import text

from api.config import settings
from db.base import SessionLocal

router = APIRouter()


@router.get("/health")
def health(response: Response) -> dict:
    checks = {"db": False, "redis": False}

    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            checks["db"] = True
        finally:
            db.close()
    except Exception:
        pass

    try:
        r = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2)
        checks["redis"] = bool(r.ping())
    except Exception:
        pass

    if not all(checks.values()):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ok" if all(checks.values()) else "unhealthy", "checks": checks}
