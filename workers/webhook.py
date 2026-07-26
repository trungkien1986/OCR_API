"""Gửi webhook kết quả job — SSRF-safe (resolve lại + pin IP), ký HMAC bằng
`tenant_secret`, at-least-once (design/security.md Mục 10.2.1/10.8, design/api.md
Mục 9.4.2-9.4.3, design/architecture.md Mục 4.1)."""

import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

import certifi
import urllib3

from api.schemas import DocType, JobStatus, JobStatusResponse
from api.security import decrypt_secret, resolve_safe_callback, sign_webhook_payload
from db.base import SessionLocal
from db.models import Job, Tenant

logger = logging.getLogger(__name__)


def _build_payload(job: Job) -> bytes:
    payload = JobStatusResponse(
        job_id=str(job.id),
        status=JobStatus(job.status),
        doc_type=DocType(job.doc_type),
        pages_processed=job.pages_processed,
        confidence_overall=job.confidence_overall,
        extracted_data=job.extracted_data,
        validation_flags=job.validation_flags,
        review_required=job.review_required,
    )
    return payload.model_dump_json().encode("utf-8")


def _send(ip: str, hostname: str, path: str, body: bytes, headers: dict[str, str]) -> None:
    # Kết nối VẬT LÝ tới `ip` đã pin, nhưng validate TLS cert / gửi Host header theo đúng
    # `hostname` thật — cơ chế chuẩn của urllib3 cho "connect tới IP X, validate theo domain Y"
    # (design/security.md Mục 10.2.1: pin IP để chống DNS rebinding, vẫn giữ TLS đúng domain).
    pool = urllib3.HTTPSConnectionPool(
        ip,
        port=443,
        assert_hostname=hostname,
        server_hostname=hostname,
        cert_reqs="CERT_REQUIRED",
        ca_certs=certifi.where(),
        timeout=urllib3.Timeout(connect=3.0, read=5.0),
        retries=False,
    )
    try:
        resp = pool.urlopen(
            "POST",
            path,
            body=body,
            headers={**headers, "Host": hostname, "Content-Type": "application/json"},
            redirect=False,  # không tự theo redirect (Mục 10.2.1 điểm 4)
        )
    finally:
        pool.close()
    if resp.status >= 300:
        raise RuntimeError(f"webhook nhận status {resp.status}")


def deliver_webhook(job_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if job is None:
            logger.error("deliver_webhook: job_id=%s không tồn tại", job_id)
            return
        tenant = db.get(Tenant, job.tenant_id)
        if tenant is None:
            logger.error("deliver_webhook: tenant_id=%s không tồn tại (job_id=%s)", job.tenant_id, job_id)
            return

        # Resolve LẠI ngay tại thời điểm gửi, không tái dùng kết quả lúc nộp job — đây là
        # lớp chống DNS-rebinding thật sự (Mục 10.2.1 điểm 3). Nếu domain vừa bị gỡ khỏi
        # allowlist hoặc DNS đổi sang IP nội bộ kể từ lúc nộp job, lần gửi này sẽ chặn lại.
        target = resolve_safe_callback(job.callback_url, set(tenant.allowed_callback_domains))

        body = _build_payload(job)

        tenant_secret = decrypt_secret(tenant.tenant_secret_encrypted)
        headers = {"X-Signature": sign_webhook_payload(body, tenant_secret)}

        # Trong khoảng chuyển tiếp rotation (Mục 9.4.3): ký thêm bằng secret CŨ, để tenant
        # chưa kịp cập nhật verifier phía họ vẫn xác minh được — không thay thế chữ ký
        # chính, chỉ thêm header phụ.
        if tenant.tenant_secret_previous_encrypted is not None:
            previous_secret = decrypt_secret(tenant.tenant_secret_previous_encrypted)
            headers["X-Signature-Previous"] = sign_webhook_payload(body, previous_secret)

        parsed = urlparse(job.callback_url)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"

        job.webhook_delivery_attempts += 1
        db.commit()

        _send(target.ip, target.hostname, path, body, headers)

        job.webhook_delivered_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()
