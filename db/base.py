from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from api.config import settings

# connect_timeout: nếu TCP connect tới Postgres bị treo (từng thấy qua NAT/port-forward
# của Docker cả trên máy dev lẫn service container CI), fail nhanh + rõ ràng thay vì
# job lặng lẽ đứng hàng chục phút và Job.status không bao giờ thoát khỏi "queued".
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args={"connect_timeout": 10})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass
