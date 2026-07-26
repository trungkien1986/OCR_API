"""File tạm lưu trên volume tmpfs (`storage-tmp`, RAM — xem docker-compose.yml) —
TỰ ĐỘNG XOÁ ngay sau khi job đạt trạng thái cuối (design/pipeline.md Mục 8, nguyên tắc
"xoá file gốc và ảnh trung gian ngay sau khi trả kết quả")."""

import re
import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile


def sanitize_filename(filename: str | None) -> str:
    name = filename or "upload.bin"
    name = Path(name).name  # bỏ mọi phần thư mục client có thể nhét vào (path traversal)
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return name or "upload.bin"


def save_upload(job_id: uuid.UUID, upload: UploadFile, storage_dir: str) -> str:
    job_dir = Path(storage_dir) / str(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)
    dest = job_dir / sanitize_filename(upload.filename)
    with dest.open("wb") as f:
        shutil.copyfileobj(upload.file, f)
    return str(dest)


def delete_job_files(job_id: uuid.UUID, storage_dir: str) -> None:
    # ignore_errors=True: dọn dẹp không bao giờ được phép tự thành nguồn lỗi thứ 2 —
    # dù thư mục đã bị xoá trước đó hay chưa từng tồn tại, hàm này vẫn phải chạy xong êm.
    shutil.rmtree(Path(storage_dir) / str(job_id), ignore_errors=True)
