from api.security import verify_webhook_signature
from db.base import SessionLocal
from db.models import Job


def test_job_submission_end_to_end(
    client, make_tenant, sample_pdf_path, mock_public_dns, mock_webhook_delivery
):
    tenant, raw_api_key, raw_secret = make_tenant()

    with sample_pdf_path.open("rb") as f:
        resp = client.post(
            "/api/v1/jobs",
            headers={"X-API-Key": raw_api_key},
            files={"file": ("sample.pdf", f, "application/pdf")},
            data={"doc_type": "bctc", "callback_url": "https://test.example.com/webhook"},
        )

    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "queued"
    assert "schema_version" in body
    job_id = body["job_id"]

    # sync_queues (is_async=False) đã chạy process_document() và deliver_webhook() ngay
    # trong request ở trên -> job phải đạt trạng thái cuối luôn, không cần đợi worker thật.
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        assert job.status == "completed"
        assert job.file_path is None  # đã dọn file sau khi xử lý xong
    finally:
        db.close()

    # Webhook đã "gửi" (qua mock) đúng 1 lần, ký đúng bằng tenant_secret của tenant này.
    assert len(mock_webhook_delivery) == 1
    call = mock_webhook_delivery[0]
    assert call["hostname"] == "test.example.com"
    assert call["ip"] == "203.0.113.10"
    signature = call["headers"]["X-Signature"]
    assert verify_webhook_signature(call["body"], signature, raw_secret) is True

    # Polling trả về đúng shape, review_required=False cho pipeline giả (Phase 1).
    resp = client.get(f"/api/v1/jobs/{job_id}", headers={"X-API-Key": raw_api_key})
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
    assert resp.json()["review_required"] is False
