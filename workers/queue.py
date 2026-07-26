"""Factory tạo RQ Queue. Tách 2 queue riêng theo design/api.md Mục 9.2 điểm 4:
`ocr-jobs` (CPU-bound: OCR/trích xuất) và `webhook-delivery` (I/O-bound: gọi callback,
retry) — 1 webhook endpoint chậm/chết không được giữ worker OCR đang rảnh.

Test có thể monkeypatch `get_queue` để trả về Queue backed bởi fakeredis với
`is_async=False` (chạy đồng bộ trong process, không cần Redis/worker thật)."""

from functools import lru_cache

import redis
from rq import Queue

from api.config import settings


@lru_cache
def _connection() -> redis.Redis:
    return redis.Redis.from_url(settings.redis_url)


def get_queue(name: str) -> Queue:
    return Queue(name, connection=_connection())
