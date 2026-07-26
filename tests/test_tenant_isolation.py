from fastapi.testclient import TestClient


def _submit_job(client: TestClient, api_key: str, sample_pdf_path) -> str:
    with sample_pdf_path.open("rb") as f:
        resp = client.post(
            "/api/v1/jobs",
            headers={"X-API-Key": api_key},
            files={"file": ("sample.pdf", f, "application/pdf")},
            data={"doc_type": "bctc", "callback_url": "https://test.example.com/webhook"},
        )
    assert resp.status_code == 202
    return resp.json()["job_id"]


def test_tenant_can_read_own_job(client, make_tenant, sample_pdf_path, mock_public_dns, mock_webhook_delivery):
    _tenant_a, api_key_a, _secret = make_tenant()
    job_id = _submit_job(client, api_key_a, sample_pdf_path)

    resp = client.get(f"/api/v1/jobs/{job_id}", headers={"X-API-Key": api_key_a})
    assert resp.status_code == 200
    assert resp.json()["job_id"] == job_id


def test_tenant_cannot_read_other_tenants_job(
    client, make_tenant, sample_pdf_path, mock_public_dns, mock_webhook_delivery
):
    _tenant_a, api_key_a, _secret_a = make_tenant(domains=("test.example.com",))
    _tenant_b, api_key_b, _secret_b = make_tenant(domains=("other.example.com",))

    job_id = _submit_job(client, api_key_a, sample_pdf_path)

    # Tenant B tra job của tenant A -> phải trả 404 giống hệt job không tồn tại,
    # không được xác nhận sự tồn tại cho tenant không sở hữu (API1/API3).
    resp = client.get(f"/api/v1/jobs/{job_id}", headers={"X-API-Key": api_key_b})
    assert resp.status_code == 404


def test_nonexistent_job_returns_same_404(client, make_tenant):
    import uuid

    _tenant, api_key, _secret = make_tenant()
    resp = client.get(f"/api/v1/jobs/{uuid.uuid4()}", headers={"X-API-Key": api_key})
    assert resp.status_code == 404
