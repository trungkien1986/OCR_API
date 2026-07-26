import uuid

from fastapi.testclient import TestClient


def _submit(client: TestClient, headers: dict, sample_pdf_path) -> object:
    with sample_pdf_path.open("rb") as f:
        return client.post(
            "/api/v1/jobs",
            headers=headers,
            files={"file": ("sample.pdf", f, "application/pdf")},
            data={"doc_type": "bctc", "callback_url": "https://test.example.com/webhook"},
        )


def test_valid_api_key_succeeds(client, make_tenant, sample_pdf_path, mock_public_dns, mock_webhook_delivery):
    _tenant, raw_api_key, _secret = make_tenant()
    resp = _submit(client, {"X-API-Key": raw_api_key}, sample_pdf_path)
    assert resp.status_code == 202
    assert "job_id" in resp.json()


def test_missing_api_key_header_returns_401(client, sample_pdf_path):
    resp = _submit(client, {}, sample_pdf_path)
    assert resp.status_code == 401


def test_wrong_api_key_returns_401(client, make_tenant, sample_pdf_path):
    make_tenant()
    resp = _submit(client, {"X-API-Key": "totally-wrong-key"}, sample_pdf_path)
    assert resp.status_code == 401


def test_inactive_tenant_returns_401(client, make_tenant, sample_pdf_path):
    from db.base import SessionLocal
    from db.models import Tenant

    tenant, raw_api_key, _secret = make_tenant()
    db = SessionLocal()
    try:
        db_tenant = db.get(Tenant, tenant.id)
        db_tenant.is_active = False
        db.commit()
    finally:
        db.close()

    resp = _submit(client, {"X-API-Key": raw_api_key}, sample_pdf_path)
    assert resp.status_code == 401


def test_get_job_requires_api_key(client):
    resp = client.get(f"/api/v1/jobs/{uuid.uuid4()}")
    assert resp.status_code == 401
