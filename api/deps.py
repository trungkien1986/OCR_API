from collections.abc import Generator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.security import hash_api_key
from db.base import SessionLocal
from db.models import Tenant


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_tenant(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> Tenant:
    # x_api_key phải là Optional — nếu để required (`Header(...)`), FastAPI/Pydantic tự trả
    # 422 khi thiếu header TRƯỚC KHI hàm này chạy, ghi đè mất 401 mà API cần trả (design/api.md).
    if x_api_key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing api key")
    tenant = db.execute(
        select(Tenant).where(Tenant.api_key_hash == hash_api_key(x_api_key), Tenant.is_active.is_(True))
    ).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid api key")
    return tenant
