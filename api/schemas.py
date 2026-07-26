import enum
import time
from typing import Any

from pydantic import BaseModel, Field

# Bump khi đổi cấu trúc response không tương thích ngược (design/api.md Mục 9.1).
SCHEMA_VERSION = "1.0.0"


class DocType(enum.StrEnum):
    """Chưa có extractor thật cho loại nào ở Phase 1 (Tuần 4-9 mới xây) — enum này
    chỉ xác định giá trị `doc_type` hợp lệ mà API chấp nhận ngay từ bây giờ."""

    bctc = "bctc"
    cccd = "cccd"
    so_do = "so_do"
    hop_dong_cong_chung = "hop_dong_cong_chung"
    to_trinh_tin_dung = "to_trinh_tin_dung"


class JobStatus(enum.StrEnum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class JobCreateResponse(BaseModel):
    schema_version: str = SCHEMA_VERSION
    job_id: str
    status: JobStatus
    created_at: str


class JobStatusResponse(BaseModel):
    """Dùng chung cho polling (GET /api/v1/jobs/{id}) VÀ payload webhook — cùng 1 shape
    (design/api.md Mục 9). `timestamp` phục vụ chống replay khi ký webhook (Mục 10.8),
    vô hại khi chỉ dùng để polling."""

    schema_version: str = SCHEMA_VERSION
    timestamp: int = Field(default_factory=lambda: int(time.time()))
    job_id: str
    status: JobStatus
    doc_type: DocType
    pages_processed: int = 0
    confidence_overall: float | None = None
    extracted_data: dict[str, Any] = Field(default_factory=dict)
    validation_flags: list[dict[str, Any]] = Field(default_factory=list)
    review_required: bool = False
