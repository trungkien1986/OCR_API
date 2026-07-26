"""CLI dev-only — chưa có webapp/onboarding UI (Mục 3, 4.1). In `api_key` và
`tenant_secret` ĐÚNG 1 LẦN; sau đó không cách nào lấy lại nguyên văn (`api_key` chỉ lưu
hash, `tenant_secret` mã hoá lúc lưu trữ và chỉ giải mã nội bộ lúc ký webhook — Mục 9.4.3).

Dùng:
    docker compose exec api python -m scripts.create_tenant \\
        --name "Văn phòng công chứng ABC" --domain notary-abc.example.vn
"""

import argparse

from api.security import encrypt_secret, generate_api_key, generate_tenant_secret, hash_api_key
from db.base import SessionLocal
from db.models import Tenant


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="Tên tenant (vd tên văn phòng/công ty)")
    parser.add_argument(
        "--domain",
        required=True,
        action="append",
        dest="domains",
        help="Domain callback được phép (lặp lại flag này nếu có nhiều domain)",
    )
    args = parser.parse_args()

    raw_api_key = generate_api_key()
    raw_tenant_secret = generate_tenant_secret()

    tenant = Tenant(
        name=args.name,
        api_key_hash=hash_api_key(raw_api_key),
        tenant_secret_encrypted=encrypt_secret(raw_tenant_secret),
        allowed_callback_domains=args.domains,
    )

    db = SessionLocal()
    try:
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
    finally:
        db.close()

    print(f"tenant_id     : {tenant.id}")
    print(f"api_key       : {raw_api_key}        (lưu lại ngay — chỉ hiển thị 1 lần)")
    print(f"tenant_secret : {raw_tenant_secret.hex()}  (lưu lại ngay — chỉ hiển thị 1 lần)")


if __name__ == "__main__":
    main()
