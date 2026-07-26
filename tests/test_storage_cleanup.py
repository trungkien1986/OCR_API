from pathlib import Path

from api.config import settings
from db.base import SessionLocal
from db.models import Job


def test_pipeline_failure_still_deletes_file_and_marks_failed(
    client, make_tenant, sample_pdf_path, mock_public_dns, mock_webhook_delivery, monkeypatch
):
    def _boom(job_id, doc_type, file_path):
        raise RuntimeError("lỗi giả lập từ pipeline")

    monkeypatch.setattr("workers.tasks.run_placeholder_pipeline", _boom)

    _tenant, raw_api_key, _secret = make_tenant()
    with sample_pdf_path.open("rb") as f:
        resp = client.post(
            "/api/v1/jobs",
            headers={"X-API-Key": raw_api_key},
            files={"file": ("sample.pdf", f, "application/pdf")},
            data={"doc_type": "bctc", "callback_url": "https://test.example.com/webhook"},
        )
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        assert job.status == "failed"
        assert job.file_path is None
        assert job.error_message is not None
        # Thông báo lỗi chỉ chứa nội dung kỹ thuật, không phải nội dung tài liệu
        # (design/security.md Mục 10.5).
        assert "lỗi giả lập từ pipeline" in job.error_message
    finally:
        db.close()

    # Không còn thư mục file nào của job này dưới STORAGE_DIR (finally trong
    # process_document đã dọn dù pipeline raise lỗi).
    job_dir = Path(settings.storage_dir) / job_id
    assert not job_dir.exists()
