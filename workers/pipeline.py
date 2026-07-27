"""Dispatch pipeline theo `doc_type` (thay thế placeholder Phase 1). Chỉ `bctc` có
extractor thật ở bước này (design/roadmap.md) — các `doc_type` khác raise
`NotImplementedError` rõ ràng thay vì giả vờ trả kết quả rỗng: `process_document`
(workers/tasks.py) bắt lỗi này như mọi lỗi pipeline khác, đánh dấu job `failed` với
thông báo kỹ thuật, KHÔNG âm thầm coi là thành công."""

import uuid
from typing import Any

from extractors.bctc import extract_bctc

_EXTRACTORS: dict[str, Any] = {
    "bctc": extract_bctc,
}


def run_pipeline(job_id: uuid.UUID, doc_type: str, file_path: str) -> dict[str, Any]:
    extractor = _EXTRACTORS.get(doc_type)
    if extractor is None:
        raise NotImplementedError(f"extractor cho doc_type={doc_type!r} chưa triển khai")
    return extractor(file_path)
