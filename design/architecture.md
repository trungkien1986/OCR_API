> Module của [OCR_ENGINE_DESIGN.md](../OCR_ENGINE_DESIGN.md) — phạm vi, kiến trúc tổng thể, ranh giới webapp, phần cứng/hạ tầng, tech stack, cấu trúc thư mục. Số mục giữ nguyên như file gốc để không phá vỡ tham chiếu chéo.

## 3. Phạm vi Giai đoạn 1 (hiện tại): CHỈ `ocr-engine`

Web app quản lý người dùng/phân quyền/thống kê để **sau**. Giai đoạn này tập trung 100% vào dịch vụ xử lý OCR độc lập, expose qua API.

## 4. Kiến trúc tổng thể

```
[Web app - sau này]                [ocr-engine - máy riêng, i5-14500/32GB, CPU-only]
  - Phân quyền, thống kê              - Nhận file qua API
  - Lưu trữ nghiệp vụ                 - OCR + nhận diện bảng + trích xuất + validate
        │                                     │
        │──── POST /api/v1/jobs (file) ──────▶│
        │◀─── webhook callback (kết quả) ─────│   (xử lý async: giây → phút)
        ▼
  Lưu kết quả về DB riêng của web app
```

2 thành phần tách biệt hoàn toàn — `ocr-engine` không lưu trữ dữ liệu lâu dài, không phụ thuộc web app để hoạt động, có thể bán như dịch vụ API độc lập cho nhiều mục đích sau này.

### 4.1 Ranh giới với webapp & tích hợp tương lai (nguyên tắc thiết kế, chưa code webapp)

Mục 3 đã chốt: webapp làm sau, giai đoạn này không thiết kế/code webapp. Nhưng để không phải đập đi làm lại khi tới lúc, cần giữ vài nguyên tắc ranh giới ngay từ bây giờ trong cách xây `ocr-engine`:

1. **Webapp là "khách hàng #1" của API công khai, không có cửa sau** — khi webapp được xây, nó gọi `ocr-engine` qua đúng API key/tenant như bất kỳ khách hàng thứ ba nào, không có đường tắt bypass xác thực chỉ vì "cùng một chủ". Giữ kỷ luật này buộc API phải đủ tốt cho người ngoài dùng thật, tránh rơi vào tình trạng "chỉ chạy được với webapp của chính mình".
2. **Mô hình tenant: mỗi khách hàng cuối (văn phòng công chứng, kế toán dịch vụ) là 1 tenant riêng** — không dồn hết vào "webapp = 1 tenant duy nhất đại diện tất cả khách hàng cuối". Lý do: giữ đúng tham vọng đã ghi ở trên ("bán như dịch vụ API độc lập cho nhiều mục đích") — nếu chỉ có 1 tenant webapp, các bên muốn tích hợp trực tiếp sau này (vd phần mềm kế toán MISA/Fast, hệ thống CSDL công chứng quốc gia) sẽ không tích hợp được mà không phải đi qua webapp.
3. **Webhook là at-least-once, không phải exactly-once** — cần ghi rõ trong tài liệu tích hợp sau này: mọi consumer (webapp lẫn bên thứ ba) phải tự dedupe theo `job_id`, vì cơ chế retry (Mục 9.3, xem [api.md](api.md)) có thể gửi trùng khi lần đầu bị timeout nhưng thực ra đã tới nơi.
4. **Chuẩn bị sẵn đoạn code mẫu verify chữ ký webhook** (không chỉ mô tả thuật toán ở Mục 10.8, xem [security.md](security.md)), để mọi consumer tương lai verify đúng ngay từ đầu, tránh mỗi bên tự implement rồi so sánh chữ ký không constant-time:

```python
import hmac, hashlib

def verify_webhook_signature(body: bytes, signature_header: str, tenant_secret: str) -> bool:
    expected = hmac.new(tenant_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)  # KHÔNG dùng "==" — lộ timing attack
```

5. **Chính sách ổn định API rõ ràng khi có consumer thật đầu tiên** — một khi webapp (và có thể bên thứ ba khác) phụ thuộc vào `/api/v1/`, thay đổi breaking phải thông báo trước tối thiểu vài tháng và chạy song song version mới, không đổi ngầm — áp dụng đúng tinh thần `schema_version` đã có ở Mục 9.1.
6. **Ranh giới trách nhiệm dữ liệu cá nhân sẽ tách làm 2** khi webapp bắt đầu lưu trữ lâu dài (khác hẳn `ocr-engine` chỉ xử lý thoáng qua rồi xoá — Mục 10.1) — cần xác định lại vai trò kiểm soát dữ liệu giữa `ocr-engine` và webapp ở thời điểm đó; chưa cần giải quyết ngay, chỉ ghi nhận để không quên.

## 5. Phần cứng

| | Cấu hình |
|---|---|
| Máy `ocr-engine` | i5-14500 (14 core/20 luồng), 32GB RAM, SSD ≥300GB, **không cần GPU** |
| Lý do đủ dùng | PaddleOCR PP-OCRv5 chạy tốt CPU-only qua ONNX/OpenVINO; benchmark GPU rẻ nhất (RTX 4060: ~110 trang/phút) đã dư hàng chục lần nhu cầu thực tế pilot — CPU thường càng dư sức cho quy mô pilot |
| Nâng cấp GPU sau | Chỉ cần khi bổ sung fallback Vision-LLM cho case khó (viết tay/scan xấu) — không phải yêu cầu MVP |

### 5.1 Hệ điều hành & triển khai (đã chốt)

- **Hệ điều hành**: Ubuntu Server (không cần GUI), không dùng Windows — máy này dành riêng cho `ocr-engine`, không dùng chung việc khác. Lý do: PaddleOCR/OpenVINO và Redis đều native, ổn định hơn trên Linux; `systemd` quản lý service (auto-restart, log qua journald, giới hạn tài nguyên qua cgroups) trưởng thành hơn Windows Service; tránh overhead ảo hoá của Docker Desktop trên Windows (WSL2/Hyper-V) — đáng kể với workload CPU-only đã tính sát nhu cầu thực tế.
- **Đóng gói**: containerize toàn bộ bằng Docker — 1 `docker-compose.yml` cho API + worker + Redis, quản lý bằng restart policy (`restart: unless-stopped`); không chạy native process rời rạc rồi tự bọc bằng NSSM/Windows Service.
- **Model OCR (PaddleOCR/PP-StructureV3) được bake sẵn vào Docker image lúc build** (`RUN python -c "..."` gọi trước để tải/khởi tạo model, đặt trước `COPY . .` để tận dụng cache layer), KHÔNG tải lazy lúc chạy job đầu tiên — khớp thực tế Mục 9.5 (xem [api.md](api.md)): máy production chưa chắc có internet ổn định, không thể phó mặc việc tải model vào đúng lúc có job thật tới.
- **Khả năng chạy trên Windows khi cần (demo/máy dự phòng)**: gần như miễn phí nhờ đã containerize — cùng `docker-compose.yml` chạy được trên Docker Desktop (Windows) mà không cần sửa code, miễn giữ kỷ luật cross-platform ngay từ đầu: dùng `pathlib` thay vì hardcode dấu `/`, không gọi lệnh shell đặc thù OS, không hardcode đường dẫn kiểu `/tmp/...`.
- Không đi hướng "triển khai native song song 2 hệ điều hành" (systemd unit riêng cho Linux + NSSM/Windows Service riêng cho Windows) — tốn công bảo trì gấp đôi mỗi lần đổi cấu hình.

### 5.2 CI/CD — quy trình từ code tới production (mới, chưa có trước đây)

**Git hosting: GitHub, repo private** (đúng nguyên tắc Mục 1 — hoàn toàn tách biệt repo ngân hàng). Lý do: tích hợp sẵn GitHub Actions (CI) + GitHub Container Registry (lưu Docker image) trong cùng hệ sinh thái, không cần thêm dịch vụ thứ ba.

**CI (chạy mỗi lần push/PR):**
1. Lint (`ruff`) + type check (`mypy`)
2. Unit test + validate JSON Schema (Mục 9.1, xem [api.md](api.md))
3. Build Docker image, quét lỗ hổng (Trivy — Mục 10.6, xem [security.md](security.md)) + sinh SBOM
4. Push image lên GitHub Container Registry, gắn tag theo git SHA (immutable — phục vụ rollback)

**Regression gate golden dataset (Mục 14.3, xem [testing.md](testing.md)) tách khỏi CI nhanh** — chạy OCR thật trên máy CPU-only tốn thời gian hơn hẳn lint/unit test, không nên chặn mỗi lần push. Chạy đầy đủ khi merge vào `main` hoặc theo lịch (nightly), không chặn từng commit trên feature branch — giữ vòng lặp phát triển nhanh mà vẫn có gate trước khi lên production.

**CD (khi merge vào `main`):**
- Dùng **self-hosted GitHub Actions runner cài ngay trên máy `ocr-engine`** — đơn giản hơn hẳn runner cloud rồi SSH vào máy, vì production là 1 máy cố định duy nhất, không phải hạ tầng ảo hoá co giãn
- Có **cổng duyệt thủ công** (GitHub Environments + required reviewer) trước khi deploy thật — vì đang xử lý dữ liệu cá nhân/tài chính nhạy cảm của khách hàng pilot thật, chưa nên auto-deploy hoàn toàn tự động ở giai đoạn này; tự động hoá đầy đủ có thể cân nhắc sau khi hệ thống đủ trưởng thành
- Quy trình: chạy migration DB trước → `docker compose pull` (image mới theo tag SHA) → `docker compose up -d` → gọi lại healthcheck đã có sẵn trong `docker-compose.yml` để xác nhận thành công → nếu fail, tự rollback về tag image trước đó

**Vì sao không cần zero-downtime/blue-green:** kiến trúc đã async qua Redis Queue (Mục 6) — job đang chờ trong queue vẫn an toàn qua vài giây restart container, không mất dữ liệu. Đầu tư blue-green/canary ở quy mô pilot 2-3 khách hàng là over-engineering, không tương xứng lợi ích.

**Ranh giới secrets quan trọng:** file `.env` trên máy production (chứa `API_KEY`, DB credentials thật) **không nằm trong git, không bị CD ghi đè mỗi lần deploy** — chỉ code/image thay đổi, secrets vận hành sống độc lập trên máy. Secrets dùng trong CI (thông tin đăng nhập registry...) lưu ở GitHub Actions Secrets, tách biệt hoàn toàn khỏi secrets nghiệp vụ (`tenant_secret`/`api_key` của khách hàng — những cái này là dữ liệu runtime trong Postgres, không phải CI secret).

## 6. Tech stack đề xuất

- **API**: FastAPI (Python) — tái dùng kinh nghiệm sẵn có
- **Queue xử lý nền**: RQ (Redis Queue) — nhẹ hơn Celery, đủ dùng cho 1 máy đơn ở quy mô pilot
- **OCR**: PaddleOCR (Apache 2.0), dùng `lang="vi"` — **sửa lại nhận định sai ở đây trước đó**: PP-OCRv5 (dòng model mới nhất của PaddleOCR) thực ra chỉ hỗ trợ 5 ngôn ngữ (Trung giản/phồn thể, pinyin, Anh, Nhật), KHÔNG có tiếng Việt native. Hỗ trợ tiếng Việt nằm ở dòng model đa ngôn ngữ khác của cùng thư viện PaddleOCR (tham số `lang="vi"`, ~100+ ngôn ngữ) — vẫn là cùng 1 thư viện/license, chỉ khác lựa chọn model bên trong. Vẫn cần tự benchmark so với VietOCR chuyên biệt trên mẫu thật trước khi chốt (Tuần 9-10).
- **Nhận diện bảng**: PP-StructureV3 (tên hiện tại của dòng "PP-Structure" trong PaddleOCR 3.x) — bắt buộc cho BCTC vì đây là bảng dày đặc, không phải văn bản thường
- **Field extraction hồ sơ tín dụng/công chứng**: không dùng 1 chiến lược duy nhất cho mọi loại giấy tờ — mẫu nhà nước đã chuẩn hoá (CCCD, sổ đỏ) dùng rule-based theo vị trí + tận dụng MRZ/QR có sẵn; giấy tờ tự do/theo mẫu riêng từng tổ chức (hợp đồng công chứng, tờ trình tín dụng) dùng pattern-anchored (regex quanh từ khoá) + template cấu hình theo tenant, mở rộng từ pattern đã quen (parser SWIFT/giấy báo). Chi tiết ở Mục 8.3-8.5, xem [pipeline.md](pipeline.md).

## 7. Cấu trúc thư mục

```
ocr-engine/
├── api/                # FastAPI app, endpoint nhận job
├── workers/            # RQ worker: OCR + extract + validate
├── extractors/            # 1 file/loại tài liệu — chia theo mẫu giấy tờ cụ thể, không theo "nhóm nghiệp vụ"
│   ├── bctc.py              # ĐÃ CÓ (v1): ghép preprocess + OCR + PP-StructureV3 + map mã số + rule engine
│   ├── ma_so_200.py          # ĐÃ CÓ: danh mục mã số Thông tư 200 (Mẫu B01-DN) — xem Mục 13 (roadmap.md) về lý do đổi từ Thông tư 133
│   ├── number_parser.py       # ĐÃ CÓ: parser số kiểu Việt Nam (chấm nghìn, phẩy thập phân, số âm trong ngoặc)
│   ├── cccd.py               # CHƯA CÓ — ưu tiên MRZ/QR trước OCR text tự do (Mục 8.3)
│   ├── so_do.py               # CHƯA CÓ — theo version mẫu GCN QSDĐ (Mục 8.4)
│   ├── hop_dong_cong_chung.py  # CHƯA CÓ — pattern-anchored quanh trường bắt buộc theo Luật Công chứng (Mục 8.5)
│   └── to_trinh_tin_dung.py    # CHƯA CÓ — đọc template cấu hình theo tenant, không hardcode 1 mẫu (Mục 8.5)
├── templates/            # CHƯA CÓ — định nghĩa field-position/keyword theo tenant (to_trinh_tin_dung, mẫu sổ đỏ theo thời kỳ)
├── ocr/                  # ĐÃ CÓ: engine.py (wrapper PaddleOCR lang="vi"), preprocess.py (text layer/rasterize/deskew), table.py (wrapper PP-StructureV3)
├── validation/           # ĐÃ CÓ (mới, chưa có ở bản gốc): engine.py (rule engine cấu hình YAML, Mục 8.6) + rules_bctc.yaml
├── storage/              # xử lý file tạm — TỰ ĐỘNG XOÁ sau khi trả kết quả
├── tests/
│   └── fixtures/bctc/    # ĐÃ CÓ 2 BCTC công khai thật (HOSE/HNX) làm hạt giống golden dataset — KHÔNG BAO GIỜ dữ liệu thật của khách hàng
└── docs/
```
