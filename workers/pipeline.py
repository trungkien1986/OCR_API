"""*** PHASE 1 PLACEHOLDER — KHÔNG PHẢI OCR THẬT ***

Việc duy nhất của hàm này là chứng minh luồng queued -> processing -> completed/failed
(queue -> worker -> DB -> webhook) chạy đúng đầu-cuối. Sẽ được thay bằng pipeline OCR
thật (PaddleOCR/PP-Structure + 5 extractor theo loại giấy tờ + rule engine validate) ở
Tuần 2-9 theo design/roadmap.md — KHÔNG thêm logic trích xuất nào ở đây.
"""

import uuid
from typing import Any, TypedDict


class PlaceholderPipelineResult(TypedDict):
    pages_processed: int
    confidence_overall: float | None
    extracted_data: dict[str, Any]
    validation_flags: list[dict[str, Any]]
    review_required: bool


def run_placeholder_pipeline(job_id: uuid.UUID, doc_type: str, file_path: str) -> PlaceholderPipelineResult:
    return {
        "pages_processed": 0,
        "confidence_overall": None,
        "extracted_data": {},
        "validation_flags": [],
        "review_required": False,
    }
