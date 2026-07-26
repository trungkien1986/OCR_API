import uuid

import fakeredis
from rq import Queue, Worker

from db.base import SessionLocal
from db.models import Job
from workers.tasks import process_document


def test_process_document_survives_real_rq_roundtrip(
    make_tenant, mock_public_dns, mock_webhook_delivery
):
    """Khác với các test khác (dùng is_async=False qua fixture `sync_queues` trong
    conftest.py — chạy hàm trực tiếp, không qua serialize), test này dùng Queue/Worker
    THẬT trên fakeredis để bắt các lỗi enqueue/serialize thật (vd tham số không pickle
    được) mà chế độ is_async=False sẽ che giấu."""
    tenant, _api_key, _secret = make_tenant()

    db = SessionLocal()
    try:
        job = Job(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            doc_type="bctc",
            status="queued",
            callback_url="https://test.example.com/webhook",
            file_path="/data/storage/khong-can-ton-tai-that",
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = str(job.id)
    finally:
        db.close()

    fake_conn = fakeredis.FakeStrictRedis()
    queue = Queue("ocr-jobs-test", connection=fake_conn)
    queue.enqueue(process_document, job_id)

    worker = Worker([queue], connection=fake_conn)
    worker.work(burst=True)

    db = SessionLocal()
    try:
        refreshed = db.get(Job, job_id)
        assert refreshed.status == "completed"
    finally:
        db.close()
