import time

import psycopg
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from api.config import settings

_url = make_url(settings.database_url)


def _connect_with_retry() -> psycopg.Connection:
    # Đã quan sát thấy (cả máy dev lẫn service container Postgres của GitHub Actions CI)
    # 1 lần mở connection MỚI thỉnh thoảng bị treo/timeout dù Postgres đang khoẻ và số
    # connection hiện tại còn thấp — nghẽn thoáng qua ở tầng mạng/NAT container, không lặp
    # lại ngay. Thử lại vài lần với connect_timeout ngắn thay vì để 1 lần trục trặc làm
    # cả job/request thất bại.
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            return psycopg.connect(
                host=_url.host,
                port=_url.port or 5432,
                user=_url.username,
                password=_url.password,
                dbname=_url.database,
                connect_timeout=10,
            )
        except psycopg.OperationalError as exc:
            last_exc = exc
            time.sleep(0.5 * (attempt + 1))
    assert last_exc is not None
    raise last_exc


engine = create_engine(settings.database_url, pool_pre_ping=True, creator=_connect_with_retry)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass
