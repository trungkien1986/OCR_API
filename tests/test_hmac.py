from api.security import sign_webhook_payload, verify_webhook_signature


def test_roundtrip_sign_then_verify():
    secret = b"a" * 32
    body = b'{"job_id": "abc", "status": "completed"}'
    signature = sign_webhook_payload(body, secret)
    assert verify_webhook_signature(body, signature, secret) is True


def test_tampered_body_fails_verification():
    secret = b"a" * 32
    body = b'{"job_id": "abc", "status": "completed"}'
    signature = sign_webhook_payload(body, secret)
    tampered = body.replace(b"completed", b"failed!!")
    assert verify_webhook_signature(tampered, signature, secret) is False


def test_tampered_signature_fails_verification():
    secret = b"a" * 32
    body = b'{"job_id": "abc", "status": "completed"}'
    signature = sign_webhook_payload(body, secret)
    tampered_signature = ("0" if signature[0] != "0" else "1") + signature[1:]
    assert verify_webhook_signature(body, tampered_signature, secret) is False


def test_different_secret_fails_verification():
    body = b'{"job_id": "abc"}'
    signature = sign_webhook_payload(body, b"secret-one-32-bytes-padding-aaaa")
    assert verify_webhook_signature(body, signature, b"secret-two-32-bytes-padding-bbbb") is False
