import socket

import pytest

from api.security import resolve_safe_callback


def _mock_getaddrinfo(monkeypatch: pytest.MonkeyPatch, ip: str) -> None:
    def _fake(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]

    monkeypatch.setattr(socket, "getaddrinfo", _fake)


def test_rejects_non_https():
    with pytest.raises(ValueError, match="https"):
        resolve_safe_callback("http://example.com/webhook", {"example.com"})


def test_rejects_ip_literal_host():
    with pytest.raises(ValueError, match="IP trực tiếp"):
        resolve_safe_callback("https://203.0.113.5/webhook", {"203.0.113.5"})


def test_rejects_domain_not_allowlisted():
    with pytest.raises(ValueError, match="đăng ký"):
        resolve_safe_callback("https://not-registered.example.com/webhook", {"example.com"})


@pytest.mark.parametrize(
    "blocked_ip",
    [
        "127.0.0.1",
        "10.0.0.5",
        "172.16.0.1",
        "192.168.1.1",
        "169.254.169.254",  # cloud metadata
        "::1",
        "fc00::1",
    ],
)
def test_rejects_each_blocked_range(monkeypatch: pytest.MonkeyPatch, blocked_ip: str):
    _mock_getaddrinfo(monkeypatch, blocked_ip)
    with pytest.raises(ValueError, match="nội bộ"):
        resolve_safe_callback("https://example.com/webhook", {"example.com"})


def test_accepts_public_ip_and_pins_it(monkeypatch: pytest.MonkeyPatch):
    _mock_getaddrinfo(monkeypatch, "203.0.113.10")
    target = resolve_safe_callback("https://example.com/webhook", {"example.com"})
    assert target.hostname == "example.com"
    # Phải là IP đã pin, không phải hostname — đây chính là điều được dùng để chống
    # DNS rebinding khi mở kết nối thật (design/security.md Mục 10.2.1 điểm 3).
    assert target.ip == "203.0.113.10"


def test_checks_all_returned_addresses_not_just_first(monkeypatch: pytest.MonkeyPatch):
    # địa chỉ đầu tiên hợp lệ (public), địa chỉ thứ 2 thuộc dải bị chặn -> vẫn phải từ chối
    def _fake(host, port, *args, **kwargs):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("203.0.113.10", port)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", port)),
        ]

    monkeypatch.setattr(socket, "getaddrinfo", _fake)
    with pytest.raises(ValueError, match="nội bộ"):
        resolve_safe_callback("https://example.com/webhook", {"example.com"})
