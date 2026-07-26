import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.config import settings
from api.deps import get_current_tenant, get_db
from api.schemas import DocType, JobCreateResponse, JobStatus, JobStatusResponse
from api.security import resolve_safe_callback
from db.models import Job, Tenant
from storage.files import save_upload
from workers.queue import get_queue
from workers.tasks import process_document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


def _upload_size_bytes(file: UploadFile) -> int:
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    return size


@router.post("", response_model=JobCreateResponse, status_code=status.HTTP_202_ACCEPTED)
def create_job(
    file: UploadFile = File(...),
    doc_type: DocType = Form(...),
    callback_url: str = Form(...),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> JobCreateResponse:
    try:
        resolve_safe_callback(callback_url, set(tenant.allowed_callback_domains))
    except ValueError as exc:
        # Log lại việc từ chối — tín hiệu nghi dò quét/tenant cấu hình sai
        # (design/security.md Mục 10.2.1 điểm 6). Không log callback_url nguyên văn
        # nếu nó có thể chứa thông tin nhạy cảm — chỉ log tenant_id + lý do.
        logger.warning("callback_url bị từ chối tenant_id=%s reason=%s", tenant.id, exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    # Giới hạn kích thước file — vệ sinh DoS cơ bản (design/security.md Mục 10.2 API4).
    # Input hardening đầy đủ (magic byte, virus scan, giới hạn số trang — Mục 10.4)
    # nằm ngoài phạm vi Phase 1.
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if _upload_size_bytes(file) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"file vượt quá giới hạn {settings.max_upload_mb}MB",
        )

    job = Job(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        doc_type=doc_type.value,
        status=JobStatus.queued.value,
        callback_url=callback_url,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    job.file_path = save_upload(job.id, file, settings.storage_dir)
    db.commit()
    job_id_str = str(job.id)
    created_at_iso = job.created_at.isoformat()
    # Trả connection về pool NGAY trước khi enqueue — enqueue có thể chạy job đồng bộ
    # (is_async=False, chỉ trong test) và mở 1 session Postgres MỚI cùng luồng; giữ
    # session này mở song song từng gây treo lúc mở connection thứ 2 (xem db/base.py).
    db.close()

    get_queue("ocr-jobs").enqueue(process_document, job_id_str)

    return JobCreateResponse(
        job_id=job_id_str,
        status=JobStatus.queued,
        created_at=created_at_iso,
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job(
    job_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> JobStatusResponse:
    # Lọc theo CẢ id lẫn tenant_id trong cùng 1 mệnh đề WHERE — job của tenant khác trả
    # về 404 giống hệt job không tồn tại, không xác nhận sự tồn tại cho tenant không sở
    # hữu (design/security.md Mục 10.2 API1/API3).
    job = db.execute(select(Job).where(Job.id == job_id, Job.tenant_id == tenant.id)).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")

    return JobStatusResponse(
        job_id=str(job.id),
        status=JobStatus(job.status),
        doc_type=DocType(job.doc_type),
        pages_processed=job.pages_processed,
        confidence_overall=job.confidence_overall,
        extracted_data=job.extracted_data,
        validation_flags=job.validation_flags,
        review_required=job.review_required,
    )
