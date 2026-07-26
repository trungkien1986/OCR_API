"""Bootstrap biến môi trường TRƯỚC khi import bất kỳ module nào của project — `api.config
.Settings` đọc env lúc import module (`settings = Settings()`), nên phải set env ở đây
sớm nhất có thể. pytest đảm bảo conftest.py trong 1 thư mục được nạp trước mọi test
module trong thư mục đó."""

import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://ocr:test@localhost:5432/ocr_engine_test",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("STORAGE_DIR", os.path.join(os.path.dirname(__file__), "_tmp_storage"))
os.environ.setdefault("MAX_UPLOAD_MB", "25")

from cryptography.fernet import Fernet  # noqa: E402

# Khoá Fernet cố định chỉ dùng cho test — KHÔNG dùng lại giá trị này ở môi trường thật.
os.environ.setdefault("SECRET_ENCRYPTION_KEY", Fernet.generate_key().decode())

import shutil  # noqa: E402
from pathlib import Path  # noqa: E402

import fakeredis  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from rq import Queue  # noqa: E402
from sqlalchemy import text  # noqa: E402

from api.config import settings  # noqa: E402
from api.main import app  # noqa: E402
from api.security import encrypt_secret, generate_api_key, generate_tenant_secret, hash_api_key  # noqa: E402
from db.base import Base, SessionLocal, engine  # noqa: E402
from db.models import Tenant  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    # Đường thật (production/CI) luôn chạy `alembic upgrade head` riêng — cái này chỉ là
    # lưới an toàn để `pytest` chạy độc lập không phụ thuộc phải nhớ chạy alembic trước
    # (create_all không lỗi nếu bảng đã tồn tại từ migration).
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(autouse=True)
def clean_tables():
    # Dọn sạch 2 bảng trước MỖI test — đơn giản hơn nhiều so với transaction-rollback
    # lồng nhau, và đúng đắn cho cả 2 kiểu Session đang dùng trong codebase (FastAPI DI
    # `get_db()` lẫn `SessionLocal()` gọi trực tiếp trong workers/).
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM jobs"))
        conn.execute(text("DELETE FROM tenants"))
    yield


@pytest.fixture(autouse=True)
def _clean_storage_dir():
    yield
    shutil.rmtree(settings.storage_dir, ignore_errors=True)


@pytest.fixture(autouse=True)
def sync_queues(monkeypatch):
    """Chạy RQ đồng bộ trong process (is_async=False, fakeredis) — không cần Redis/worker
    thật cho phần lớn test. test_worker_integration.py tự ghi đè lại bằng queue bất đồng
    bộ thật (fakeredis + Worker.work) trong phạm vi riêng của nó."""
    fake_conn = fakeredis.FakeStrictRedis()

    def _get_queue(name: str) -> Queue:
        return Queue(name, connection=fake_conn, is_async=False)

    # Patch tại đúng nơi mỗi module đã "from workers.queue import get_queue" —
    # patch riêng workers.queue.get_queue không đủ vì tên đã được import vào namespace khác.
    monkeypatch.setattr("workers.queue.get_queue", _get_queue)
    monkeypatch.setattr("api.routers.jobs.get_queue", _get_queue)
    monkeypatch.setattr("workers.tasks.get_queue", _get_queue)
    yield fake_conn


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def make_tenant():
    """Tạo 1 Tenant thật trong DB test, trả về (tenant, raw_api_key, raw_tenant_secret)."""

    def _make(domains: tuple[str, ...] = ("test.example.com",)) -> tuple[Tenant, str, bytes]:
        raw_api_key = generate_api_key()
        raw_secret = generate_tenant_secret()
        db = SessionLocal()
        try:
            tenant = Tenant(
                name="Tenant test",
                api_key_hash=hash_api_key(raw_api_key),
                tenant_secret_encrypted=encrypt_secret(raw_secret),
                allowed_callback_domains=list(domains),
            )
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
        finally:
            db.close()
        return tenant, raw_api_key, raw_secret

    return _make


@pytest.fixture()
def sample_pdf_path() -> Path:
    return Path(__file__).parent / "fixtures" / "sample.pdf"


@pytest.fixture()
def mock_public_dns(monkeypatch: pytest.MonkeyPatch):
    """Giả lập DNS resolve callback domain của test ra 1 IP public — để
    resolve_safe_callback() (Mục 10.2.1) không chặn nhầm domain test hợp lệ."""
    import socket

    def _fake(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("203.0.113.10", port))]

    monkeypatch.setattr(socket, "getaddrinfo", _fake)


@pytest.fixture()
def mock_webhook_delivery(monkeypatch: pytest.MonkeyPatch):
    """Chặn không cho workers.webhook thật sự gọi ra mạng — trả về response giả 200 OK,
    ghi lại mọi lệnh gọi (url, body, headers) để test assert nội dung/chữ ký."""
    calls: list[dict] = []

    class _FakeResponse:
        status = 200

    class _FakePool:
        def __init__(self, ip, **kwargs):
            self.ip = ip
            self.kwargs = kwargs

        def urlopen(self, method, path, body=None, headers=None, redirect=None):
            calls.append(
                {
                    "ip": self.ip,
                    "hostname": self.kwargs.get("server_hostname"),
                    "path": path,
                    "body": body,
                    "headers": headers or {},
                    "redirect": redirect,
                }
            )
            return _FakeResponse()

        def close(self):
            pass

    monkeypatch.setattr("workers.webhook.urllib3.HTTPSConnectionPool", _FakePool)
    return calls
