import uuid
from datetime import datetime

from sqlalchemy import (
    ARRAY,
    TIMESTAMP,
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # api_key: hash tra cứu xác định (SHA-256), KHÔNG dùng bcrypt/argon2 — api_key là
    # token ngẫu nhiên entropy cao do server sinh (không phải mật khẩu dễ đoán), và salt
    # ngẫu nhiên của bcrypt sẽ phá index tra cứu này (design/api.md Mục 9.4 — xem api/security.py).
    api_key_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # tenant_secret: MÃ HOÁ lúc lưu trữ (không phải hash một chiều) — ocr-engine cần giá
    # trị gốc để ký HMAC mỗi lần gửi webhook (design/api.md Mục 9.4.3, đã sửa lại đúng ở
    # Phase 1 sau khi phát hiện bản gốc ghi nhầm "lưu dạng băm"). Hỗ trợ rotation: 2 secret
    # song song trong thời gian chuyển tiếp, không cần bảng lịch sử ở quy mô pilot.
    tenant_secret_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    tenant_secret_previous_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    tenant_secret_previous_expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    # Domain callback đã đăng ký trước — chống SSRF bằng allowlist, không nhận URL tự do
    # mỗi job (design/security.md Mục 10.2.1).
    allowed_callback_domains: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")

    # Có cột sẵn, CHƯA enforce ở Phase 1 (cần quyết định nơi lưu trạng thái token-bucket
    # dùng chung, chỉ có ý nghĩa khi >1 API replica hoặc tenant thực sự cần giới hạn).
    rate_limit_per_minute: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_tenants_api_key_hash", "api_key_hash", unique=True),)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    doc_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="queued")
    callback_url: Mapped[str] = mapped_column(Text, nullable=False)

    pages_processed: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    confidence_overall: Mapped[float | None] = mapped_column(Float, nullable=True)
    extracted_data: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    validation_flags: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    # Chỉ thông tin kỹ thuật — KHÔNG BAO GIỜ chứa nội dung tài liệu (design/security.md Mục 10.5).
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Null sau khi đã xoá file — kiêm tín hiệu audit "đã dọn dẹp hay chưa".
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    webhook_delivery_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    webhook_delivered_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (Index("ix_jobs_tenant_created", "tenant_id", "created_at"),)
