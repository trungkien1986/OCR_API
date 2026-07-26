# Phase 1 ("Tuần 1") — Hạ tầng, mô hình tenant/API key, chống SSRF, ký HMAC webhook

## Bối cảnh

`OCR_ENGINE_DESIGN.md` + `design/*.md` trong `C:\OCR_API_plan` giờ đã bao phủ toàn bộ dự án (kinh doanh, kiến trúc, pipeline, API, bảo mật, roadmap, testing) khá chi tiết sau nhiều vòng rà soát. Chưa có dòng code nào — chỉ có `docker-compose.yml`, `Dockerfile`, `requirements.txt`, `.env.example`, `.dockerignore` làm khung sườn, và chưa có git repo.

Người dùng yêu cầu bắt đầu biến kế hoạch thành code, từng phần theo `design/roadmap.md`. Kế hoạch này **chỉ bao phủ "Tuần 1"**, phạm vi đã được chốt sẵn trong chính dòng roadmap: *"Hạ tầng: docker-compose.yml (API+worker+Redis+Postgres), CI/CD đầy đủ, API key + tenant model, khung chống SSRF cho `callback_url` + ký HMAC webhook ngay từ đầu."* Mọi thứ khác (pipeline OCR thật, 5 extractor theo loại giấy tờ, rule engine validate nghiệp vụ, golden dataset) rõ ràng thuộc các tuần sau và **không** đụng tới ở đây — mục tiêu của phase này là 1 bộ khung chạy được, có test: tạo được tenant, tenant nộp được job, job chạy qua queue, và webhook đã ký được gửi trả về — với 1 "pipeline" giả (placeholder) đứng thay cho OCR thật.

Có 2 điểm cần nêu rõ trước khi code:
- **Code nằm trực tiếp trong `C:\OCR_API_plan`**, không tạo thư mục con `ocr-engine/` — vì `docker-compose.yml`/`Dockerfile` đã dùng `.` làm build context ngay tại đó, làm vậy tránh phải sửa lại đường dẫn. Tên/vị trí thư mục cuối cùng của dự án (vẫn là mục còn mở ở `design/roadmap.md` Mục 13) chỉ là việc đổi tên thư mục ngoài cùng, có thể làm bất cứ lúc nào sau này mà không đụng tới code bên trong.
- **`design/api.md` Mục 9.4.3 có 1 lỗi sai thực tế cần sửa trong phase này**: tài liệu ghi `tenant_secret` nên lưu dạng băm một chiều (hash), giống `api_key`. Đó là sai — `ocr-engine` phải ký mọi webhook gửi đi bằng `HMAC-SHA256(body, tenant_secret)`, việc này cần **giá trị gốc** của secret tại thời điểm gửi. Băm một chiều khiến việc đó bất khả thi. Mô hình đúng (và là cái kế hoạch này sẽ code) là: `tenant_secret` được **mã hoá lúc lưu trữ (encrypt at rest)** bằng khoá phía server (`cryptography.fernet`), chỉ giải mã trong bộ nhớ đúng lúc ký, không bao giờ trả lại qua bất kỳ API nào sau khi tạo lần đầu. Sẽ cần sửa nhỏ `design/api.md` song song với code.

## Cấu trúc thư mục (mới)

```
C:\OCR_API_plan\
├── api\
│   ├── __init__.py
│   ├── main.py              # FastAPI() app, routers, startup/shutdown
│   ├── config.py            # pydantic-settings: DATABASE_URL, REDIS_URL, STORAGE_DIR, SECRET_ENCRYPTION_KEY, MAX_UPLOAD_MB
│   ├── deps.py               # get_db(), get_current_tenant() (xác thực API key)
│   ├── security.py           # hash_api_key, generate_api_key/tenant_secret, encrypt/decrypt_secret, sign_webhook_payload, resolve_safe_callback
│   ├── schemas.py             # Enum DocType/JobStatus, JobCreateResponse, JobStatusResponse (có schema_version + timestamp)
│   └── routers\
│       ├── jobs.py            # POST /api/v1/jobs, GET /api/v1/jobs/{id}
│       └── health.py          # GET /health (kiểm tra DB + Redis)
├── workers\
│   ├── queue.py               # factory tạo RQ Queue cho "ocr-jobs" và "webhook-delivery"
│   ├── pipeline.py             # run_placeholder_pipeline() — hàm giả, đánh dấu rõ ràng, thay bằng thật ở Tuần 2-9
│   ├── tasks.py                # process_document(job_id): queued→processing→completed/failed, luôn dọn file, đẩy job ký webhook
│   └── webhook.py               # deliver_webhook(job_id): resolve lại IP SSRF-safe, ký, gửi qua urllib3, dùng RQ Retry
├── db\
│   ├── base.py                  # engine, SessionLocal, declarative Base
│   ├── models.py                 # Tenant, Job
│   └── migrations\ (Alembic)     # env.py, versions/0001_initial.py
├── storage\
│   └── files.py                  # save_upload(), delete_job_files() (luôn chạy qua try/finally)
├── scripts\
│   └── create_tenant.py           # CLI dev-only: in api_key + tenant_secret đúng 1 lần
├── docs\schemas\                   # JSON Schema sinh ra (Mục 9.1), CI kiểm tra luôn đồng bộ
├── tests\
│   ├── conftest.py, fixtures/sample.pdf
│   ├── test_ssrf.py, test_hmac.py, test_auth.py, test_tenant_isolation.py,
│   │   test_jobs_api.py, test_storage_cleanup.py, test_worker_integration.py
├── .github\workflows\ci.yml
├── alembic.ini, pyproject.toml (cấu hình ruff/mypy/pytest)
├── requirements.txt (cập nhật), requirements-dev.txt (mới)
├── docker-compose.yml (cập nhật), .env.example (cập nhật)
└── .gitignore (mới)
```

Chưa có `extractors/`, `templates/`, `ocr/` — những phần đó thuộc Tuần 4-9.

## Các quyết định thiết kế chính của phase này

- **FastAPI đồng bộ (sync) + SQLAlchemy đồng bộ (`psycopg[binary]` v3)**, không dùng async — RQ worker vốn là process đồng bộ; chạy 2 kiểu truy cập DB khác nhau (web async, worker sync) trên cùng bảng dữ liệu không mang lại lợi ích gì ở quy mô request thấp của pilot, và FastAPI đã tự chạy handler `def` đồng bộ trong thread pool.
- **Xác thực API key bằng hash tra cứu SHA-256 xác định (deterministic)**, không dùng bcrypt/argon2 — `api_key` là token ngẫu nhiên 256-bit do server sinh ra, không phải mật khẩu dễ đoán; salt ngẫu nhiên mỗi lần hash của bcrypt sẽ khiến index `ix_tenants_api_key_hash` không tra cứu được (phải quét + so sánh chậm từng tenant mỗi request). SHA-256 mới là cái giúp tra cứu theo index O(log n) khả thi — đúng cách Stripe/GitHub/AWS xử lý token API có entropy cao.
- **`tenant_secret` mã hoá lúc lưu (Fernet, khoá lấy từ biến môi trường `SECRET_ENCRYPTION_KEY`)**, chỉ giải mã trong bộ nhớ lúc ký webhook — sửa đúng lỗi tài liệu đã nêu ở trên. Không bao giờ trả ra qua bất kỳ API nào sau khi tạo.
- **2 queue RQ ngay từ đầu**: `ocr-jobs` (CPU-bound, đã có sẵn ở service `worker`) và `webhook-delivery` (I/O-bound, service mới `worker-webhook`, giới hạn tài nguyên nhỏ hơn nhiều). Đây không phải scope creep — `design/api.md` Mục 9.2 đã coi việc tách này là quyết định chốt, để sau mới tách sẽ phải di chuyển job đang chạy dở khỏi 1 queue gộp.
- **`workers/pipeline.py` là placeholder cứng, chú thích rõ ràng** (`*** PHASE 1 PLACEHOLDER — NOT REAL OCR ***`), trả về giá trị rỗng/0 ổn định — việc duy nhất của nó là chứng minh luồng queue→worker→DB→webhook chạy đúng đầu-cuối. Không thêm bất kỳ logic OCR nào ở đây.
- **Gửi webhook resolve lại `resolve_safe_callback()` ngay tại thời điểm gửi** (không tái dùng kết quả lúc nộp job) — đây chính là lớp chống DNS-rebinding thật sự theo `design/security.md` Mục 10.2.1 điểm 3; tin vào kết quả validate từ vài phút trước sẽ mở lại đúng lỗ hổng TOCTOU mục đó đã cảnh báo.
- **Gửi qua IP đã pin bằng `urllib3.HTTPSConnectionPool`** với `assert_hostname`/`server_hostname` đặt theo đúng domain thật trong khi kết nối tới IP đã pin — cơ chế chuẩn cho "validate cert theo domain X, nhưng kết nối vật lý tới IP Y", `redirect=False` (không tự theo redirect, theo đúng điểm 4 Mục 10.2.1).
- **Postgres dùng volume lưu trữ thật**, cố tình **không** dùng tmpfs — ngược lại hoàn toàn với volume `storage-tmp` đã có: metadata job/tenant secret phải sống sót qua restart; tài liệu scan gốc thì không được phép tồn tại lâu.
- **`doc_type`/`status` là `String` thường + `Enum` Python ở tầng ứng dụng**, không dùng `ENUM` native của Postgres — tránh vướng `ALTER TYPE` mỗi lần thêm loại giấy tờ mới (Tuần 4-9 sẽ thêm nhiều loại).
- **Dùng Alembic cho migration**, không dùng file init SQL 1 lần — schema sẽ còn đổi liên tục tới Tuần 9, và quy trình CD ở `architecture.md` Mục 5.2 ("chạy migration DB trước") đã ngầm giả định có sẵn 1 công cụ migration thật.
- **Thêm cột rate-limit ngay, nhưng chưa enforce** — `Tenant.rate_limit_per_minute` có sẵn cột nhưng chưa thực thi; enforce token-bucket thật cần quyết định nơi lưu trạng thái (Redis dùng chung) — chỉ có ý nghĩa khi có hơn 1 API replica hoặc có tenant thực sự cần giới hạn. Vẫn thêm giới hạn `MAX_UPLOAD_MB` cứng ngay (rẻ, vệ sinh DoS cơ bản).
- **Tách `requirements.txt` (production, đóng gói vào image) và `requirements-dev.txt`** (thêm `pytest`, `httpx`, `fakeredis`, `ruff`, `mypy`) — giữ image production gọn, giảm bề mặt chuỗi cung ứng (`design/security.md` Mục 10.6).

## Schema Postgres (qua Alembic)

- **`Tenant`**: `id` (UUID pk), `name`, `api_key_hash` (unique index), `tenant_secret_encrypted` + `tenant_secret_previous_encrypted`/`_expires_at` (khoảng chuyển tiếp rotation — mô hình 2 secret là đủ ở quy mô pilot, không cần bảng lịch sử), `allowed_callback_domains` (`ARRAY(Text)`), `rate_limit_per_minute` (nullable, chưa enforce), `is_active`, `created_at`.
- **`Job`**: `id` (UUID pk = `job_id`), `tenant_id` (FK, index cùng `created_at`), `doc_type`, `status`, `callback_url`, `pages_processed`, `confidence_overall`, `extracted_data`/`validation_flags` (`JSONB`), `review_required`, `error_message` (chỉ kỹ thuật, không bao giờ chứa nội dung tài liệu — Mục 10.5), `file_path` (đặt về null sau khi xoá — kiêm luôn tín hiệu audit đã dọn hay chưa), `webhook_delivery_attempts`, `webhook_delivered_at`, `created_at`, `updated_at`.

## Hành vi API

- `POST /api/v1/jobs` (multipart: `file`, `doc_type`, `callback_url`; header `X-API-Key`): validate callback qua `resolve_safe_callback(url, tenant.allowed_callback_domains)` (400 + log lại việc từ chối — tín hiệu nghi dò quét theo điểm 6 Mục 10.2.1), giới hạn `MAX_UPLOAD_MB`, tạo dòng `Job`, lưu file, đẩy `process_document` vào queue `ocr-jobs`, trả về `{job_id, status: "queued", created_at, schema_version}`.
- `GET /api/v1/jobs/{id}`: lọc theo **cả** `id` lẫn `tenant_id` trong cùng 1 mệnh đề WHERE — job thuộc tenant khác trả về 404 giống hệt job không tồn tại (không bao giờ xác nhận sự tồn tại cho tenant khác — object-level auth API1/API3).
- `GET /health`: kiểm tra DB (`SELECT 1`) và Redis `PING`, trả 503 nếu lỗi (healthcheck trong compose đã trông cậy vào endpoint này).
- Response schema dùng chung có `schema_version` và trường `timestamp` (vừa đáp ứng yêu cầu versioning ở Mục 9.1, vừa đáp ứng yêu cầu chống replay ở Mục 10.8 cho payload webhook, mà không cần 2 shape khác nhau).

## Vòng đời job

`process_document(job_id)` (queue `ocr-jobs`): đánh dấu `processing` → chạy `run_placeholder_pipeline()` trong try/except → đánh dấu `completed` hoặc `failed` (chỉ `error_message` kỹ thuật) → **`finally`: luôn gọi `delete_job_files()`** (để placeholder có raise lỗi cũng không làm lộ file đã upload) → đẩy `deliver_webhook(job_id)` vào queue `webhook-delivery`, dùng `Retry` sẵn có của RQ (tái dùng, không tự viết lại — Mục 9.3).

`deliver_webhook(job_id)`: resolve lại IP callback an toàn, dựng + ký body JSON canonical, gửi qua pool `urllib3` đã pin IP, không tự theo redirect. At-least-once theo đúng thiết kế — không dedupe phía gửi (đó là việc của tenant nhận, theo `architecture.md` Mục 4.1). Khi hết lượt retry: log cảnh báo có cấu trúc (không chứa nội dung tài liệu), giữ nguyên trạng thái nghiệp vụ cuối cùng của job.

Khoảng trống còn lại đã biết, chấp nhận ở Phase 1: khối `finally` không sống sót được qua `SIGKILL`/OOM/crash máy. Vì `storage-tmp` là tmpfs, restart container đã tự xoá sạch mọi file rò rỉ, và `Job.file_path`/`status` trong Postgres cho phép vận hành viên đối chiếu lại sau đó — 1 job quét định kỳ sẽ khép kín hoàn toàn lỗ hổng này nhưng chỉ là nice-to-have, không phải yêu cầu bắt buộc của Phase 1.

## File hiện có cần cập nhật

- **`docker-compose.yml`**: thêm service `postgres:16-alpine` (volume thật `pgdata:/var/lib/postgresql/data`, healthcheck `pg_isready`); thêm service mới `worker-webhook` (`rq worker ... webhook-delivery`, giới hạn tài nguyên nhỏ, cùng kiểu `security_opt`/`cap_drop` như các service khác); `api`/`worker`/`worker-webhook` đều thêm `depends_on: postgres: condition: service_healthy` cùng biến môi trường `DATABASE_URL`/`SECRET_ENCRYPTION_KEY`.
- **`requirements.txt`**: thêm `sqlalchemy`, `alembic`, `psycopg[binary]`, `pydantic-settings`, `urllib3`, `certifi`, `cryptography`.
- **`requirements-dev.txt`** (mới): `-r requirements.txt` cộng thêm `pytest`, `httpx`, `fakeredis`, `ruff`, `mypy`.
- **`.env.example`**: bỏ dòng `API_KEY` tổng cấp cũ (auth chuyển hẳn sang api_key riêng từng tenant trong Postgres); thêm `DATABASE_URL`, `POSTGRES_*`, `SECRET_ENCRYPTION_KEY` (kèm gợi ý sinh bằng `Fernet.generate_key()` và cảnh báo mất khoá này sẽ khiến mọi `tenant_secret` đã lưu không thể khôi phục), `MAX_UPLOAD_MB`.
- **`Dockerfile`**: không cần sửa — dependency mới đều là pure-Python/wheel dựng sẵn, đã được bước `pip install -r requirements.txt` hiện có xử lý.
- **`design/api.md` Mục 9.4.3`**: sửa "lưu dạng băm" → mô tả mã hoá lúc lưu trữ + giải mã trong bộ nhớ lúc ký, khớp với code đã sửa đúng.

## CI (`.github/workflows/ci.yml`)

3 job: `lint-typecheck` (ruff check + format --check, mypy), `test` (service container `postgres:16-alpine` thật, `alembic upgrade head`, `pytest`), `build-scan-push` (phụ thuộc 2 job trên; `docker/build-push-action` → đẩy GHCR gắn tag theo SHA, `aquasecurity/trivy-action` → SARIF upload qua `github/codeql-action/upload-sarif`, `anchore/sbom-action`). Có chú thích đánh dấu rõ regression gate golden dataset và workflow CD/self-hosted-runner là `TODO` cho phase sau — chưa có máy production/runner nào để gắn vào, giả vờ có sẽ tệ hơn là để lại ghi chú thật.

## Kế hoạch test

Dùng Postgres thật cho test (không dùng SQLite — schema có `JSONB`/`ARRAY`), chạy qua `docker compose up -d postgres` ở local và service container trong GitHub Actions. RQ test qua chế độ `is_async=False` (chạy đồng bộ trong process, không cần Redis) cho phần lớn test, cộng đúng 1 test tích hợp dùng `fakeredis` + `Worker(burst=True)` để bắt các lỗi enqueue/serialize thật mà `is_async=False` sẽ che giấu.

- `test_ssrf.py` — từ chối non-https, host là IP literal, domain chưa đăng ký, từng dải CIDR trong 6 dải bị chặn (kể cả `169.254.169.254`); chấp nhận IP public đã mock; assert đúng IP đã pin (không phải hostname) được truyền vào kết nối gửi thật.
- `test_hmac.py` — round-trip ký→verify; body/chữ ký bị sửa đều fail; dùng `hmac.compare_digest`.
- `test_auth.py` / `test_tenant_isolation.py` — case key hợp lệ/thiếu/sai/tenant không active; tra job của tenant khác trả 404, không phải 403.
- `test_jobs_api.py` — đầu-cuối qua FastAPI `TestClient`: nộp job → 202 kèm `schema_version` → chạy task đồng bộ → job đạt `completed`, file đã xoá, đã thử gửi webhook (mock `urlopen`).
- `test_storage_cleanup.py` — ép pipeline giả raise lỗi → file vẫn bị xoá, `status == "failed"`, thông báo lỗi không chứa nội dung tài liệu.
- `test_worker_integration.py` — đúng 1 test dùng `fakeredis` + `Worker(burst=True)` thật.

## Các bước thực hiện

1. Sửa `design/api.md` Mục 9.4.3 (hash → mã hoá lúc lưu trữ).
2. Dựng `db/` (models, Alembic env, migration ban đầu) và cập nhật `docker-compose.yml`/`requirements*.txt`/`.env.example`.
3. Dựng `api/` (config, security, deps, schemas, routers, main).
4. Dựng `workers/` (queue, pipeline giả, tasks, webhook) và `storage/files.py`.
5. Thêm `scripts/create_tenant.py`.
6. Viết bộ test; thêm `pyproject.toml` (cấu hình ruff/mypy/pytest) và `.gitignore`.
7. Viết `.github/workflows/ci.yml`.
8. `git init` + commit đầu tiên tại local (chưa tạo remote/push — việc tạo repo GitHub và push sẽ xin xác nhận riêng với bạn sau).

## Kiểm chứng

- `pip install -r requirements-dev.txt && ruff check . && mypy .` — pass static check.
- `docker compose up -d postgres redis` (nếu máy này có Docker — sẽ xác nhận lúc thực thi) → `alembic upgrade head` → `pytest -q` — toàn bộ test pass với Postgres thật.
- Test thủ công: `docker compose up -d`, chạy `scripts/create_tenant.py` để tạo tenant, `curl -F file=@tests/fixtures/sample.pdf -F doc_type=bctc -F callback_url=https://<domain-test-đã-đăng-ký> -H "X-API-Key: <key>" http://localhost:8000/api/v1/jobs`, sau đó poll `GET /api/v1/jobs/{id}` xác nhận đạt `completed` với kết quả rỗng của placeholder, và file đã upload không còn tồn tại dưới `STORAGE_DIR`.
