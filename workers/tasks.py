import logging

from rq import Retry

from api.config import settings
from api.schemas import JobStatus
from db.base import SessionLocal
from db.models import Job
from storage.files import delete_job_files
from workers.pipeline import run_pipeline
from workers.queue import get_queue
from workers.webhook import deliver_webhook

logger = logging.getLogger(__name__)


def process_document(job_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if job is None:
            logger.error("process_document: job_id=%s không tồn tại", job_id)
            return

        job.status = JobStatus.processing.value
        db.commit()

        try:
            result = run_pipeline(job.id, job.doc_type, job.file_path or "")
            job.status = JobStatus.completed.value
            job.pages_processed = result["pages_processed"]
            job.confidence_overall = result["confidence_overall"]
            job.extracted_data = result["extracted_data"]
            job.validation_flags = result["validation_flags"]
            job.review_required = result["review_required"]
        except Exception as exc:  # noqa: BLE001 — muốn bắt mọi lỗi pipeline để luôn dọn file
            # Chỉ thông tin kỹ thuật — KHÔNG BAO GIỜ log/lưu nội dung tài liệu (Mục 10.5).
            job.status = JobStatus.failed.value
            job.error_message = str(exc)[:500]
            logger.exception("process_document thất bại job_id=%s", job_id)
        finally:
            # LUÔN chạy dù pipeline thành công/thất bại — job thất bại không được phép
            # làm rò rỉ file đã upload vĩnh viễn (design/pipeline.md Mục 8).
            delete_job_files(job.id, settings.storage_dir)
            job.file_path = None
            db.commit()

        job_id_str = str(job.id)
    finally:
        db.close()

    # Trả connection về pool TRƯỚC khi enqueue webhook — enqueue có thể chạy job đồng bộ
    # (is_async=False, chỉ trong test) và mở 1 session Postgres MỚI cùng luồng ngay lúc
    # session này còn giữ connection, từng gây treo lúc mở connection thứ 2 (db/base.py).
    get_queue("webhook-delivery").enqueue(
        deliver_webhook,
        job_id_str,
        retry=Retry(max=3, interval=[30, 120, 600]),
    )
