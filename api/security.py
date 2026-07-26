"""API key hashing, tenant_secret encryption, webhook HMAC signing, SSRF-safe callback
resolution — design/security.md Mục 10.2.1/10.8, design/api.md Mục 9.4.3."""

import hashlib
import hmac
import ipaddress
import secrets
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

from cryptography.fernet import Fernet

from api.config import settings

# ---------------------------------------------------------------------------
# API key: hash tra cứu SHA-256 xác định (deterministic), KHÔNG dùng bcrypt/argon2.
# api_key là token ngẫu nhiên entropy cao do server sinh (không phải mật khẩu dễ đoán),
# và salt ngẫu nhiên mỗi lần hash của bcrypt sẽ phá index tra cứu `ix_tenants_api_key_hash`
# (design/api.md Mục 9.4).
# ---------------------------------------------------------------------------


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


# ---------------------------------------------------------------------------
# tenant_secret: MÃ HOÁ lúc lưu trữ (không phải hash một chiều) — ocr-engine cần
# giá trị gốc để ký HMAC mỗi lần gửi webhook (design/api.md Mục 9.4.3).
# ---------------------------------------------------------------------------


def generate_tenant_secret() -> bytes:
    return secrets.token_bytes(32)


def _fernet() -> Fernet:
    return Fernet(settings.secret_encryption_key.encode())


def encrypt_secret(raw: bytes) -> bytes:
    return _fernet().encrypt(raw)


def decrypt_secret(encrypted: bytes) -> bytes:
    return _fernet().decrypt(encrypted)


# ---------------------------------------------------------------------------
# Ký/verify webhook (design/security.md Mục 10.8, design/architecture.md Mục 4.1).
# ocr-engine chỉ SIGN; verify là việc của tenant nhận — verify_webhook_signature ở đây
# tồn tại để test round-trip và làm tài liệu tham chiếu cho tenant.
# ---------------------------------------------------------------------------


def sign_webhook_payload(body: bytes, tenant_secret: bytes) -> str:
    return hmac.new(tenant_secret, body, hashlib.sha256).hexdigest()


def verify_webhook_signature(body: bytes, signature_header: str, tenant_secret: bytes) -> bool:
    expected = sign_webhook_payload(body, tenant_secret)
    return hmac.compare_digest(expected, signature_header)  # KHÔNG dùng "==" — lộ timing attack


# ---------------------------------------------------------------------------
# Chống SSRF cho callback_url (design/security.md Mục 10.2.1).
# ---------------------------------------------------------------------------

BLOCKED_NETS = [
    ipaddress.ip_network(n)
    for n in (
        "127.0.0.0/8",
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "169.254.0.0/16",  # bao gồm 169.254.169.254 — cloud metadata
        "::1/128",
        "fc00::/7",
    )
]


@dataclass(frozen=True)
class SafeCallbackTarget:
    """Kết quả resolve — pin đúng `ip` này khi mở kết nối thật, không resolve lại
    (chống DNS rebinding/TOCTOU — Mục 10.2.1 điểm 3), nhưng vẫn giữ `hostname` để
    validate TLS/gửi Host header đúng domain."""

    hostname: str
    ip: str


def resolve_safe_callback(url: str, allowed_domains: set[str]) -> SafeCallbackTarget:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("callback_url phải dùng https")
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("callback_url không có host hợp lệ")
    # Từ chối tường minh nếu host là địa chỉ IP literal, không phải domain — đây là lớp
    # phòng vệ riêng theo design/security.md Mục 10.2.1 điểm 2, không chỉ ẩn trong việc
    # domain đó có nằm trong allowlist hay không.
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass  # không phải IP literal — như kỳ vọng, tiếp tục
    else:
        raise ValueError("callback_url không được là địa chỉ IP trực tiếp, phải dùng domain")
    if hostname not in allowed_domains:
        raise ValueError("domain chưa được tenant đăng ký")
    try:
        infos = socket.getaddrinfo(hostname, 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise ValueError(f"không resolve được domain: {exc}") from exc
    if not infos:
        raise ValueError("domain không có địa chỉ IP nào")
    # Kiểm TẤT CẢ địa chỉ trả về (không chỉ địa chỉ đầu tiên) trước khi chấp nhận —
    # hardening nhỏ so với snippet tham chiếu trong design/security.md Mục 10.2.1.
    for info in infos:
        ip = str(info[4][0])
        if any(ipaddress.ip_address(ip) in net for net in BLOCKED_NETS):
            raise ValueError("callback_url trỏ vào dải mạng nội bộ — từ chối")
    return SafeCallbackTarget(hostname=hostname, ip=str(infos[0][4][0]))
