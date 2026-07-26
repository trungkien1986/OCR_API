> Module của [OCR_ENGINE_DESIGN.md](../OCR_ENGINE_DESIGN.md) — thiết kế API, chuẩn hoá định dạng, hiệu suất, reliability, quy trình vận hành, tenant_secret. Số mục giữ nguyên như file gốc để không phá vỡ tham chiếu chéo.

## 9. Thiết kế API

### Nộp tài liệu
```
POST /api/v1/jobs
```
```json
{ "job_id": "a1b2c3d4", "status": "queued", "created_at": "2026-07-26T10:00:00+07:00" }
```

### Lấy kết quả (polling hoặc webhook payload — cùng cấu trúc)
```json
{
  "job_id": "a1b2c3d4",
  "status": "completed",
  "doc_type": "bctc",
  "pages_processed": 5,
  "confidence_overall": 0.94,
  "extracted_data": {
    "bang_can_doi_ke_toan": {
      "ky_bao_cao": "2025-12-31",
      "chi_tieu": [
        {
          "ma_so": "100",
          "ten_chi_tieu": "Tài sản ngắn hạn",
          "so_cuoi_ky": 8000000000,
          "so_dau_ky": 7500000000,
          "confidence": 0.97,
          "vi_tri": { "trang": 1, "x": 120, "y": 340, "w": 200, "h": 20 }
        },
        {
          "ma_so": "270",
          "ten_chi_tieu": "TỔNG CỘNG TÀI SẢN",
          "so_cuoi_ky": 12345000000,
          "so_dau_ky": 11000000000,
          "confidence": 0.98,
          "vi_tri": { "trang": 1, "x": 120, "y": 600, "w": 200, "h": 20 }
        }
      ]
    },
    "bang_khong_chuan": [
      {
        "ten_bang": "Phụ lục tài sản cố định",
        "headers": ["Tên TSCĐ", "Nguyên giá", "Khấu hao luỹ kế", "Giá trị còn lại"],
        "rows": [["Máy móc thiết bị A", 500000000, 100000000, 400000000]]
      }
    ]
  },
  "validation_flags": [
    { "ma_so": "270", "issue": "270 ≠ 100 + 200 (lệch 5.000.000đ)", "severity": "error" }
  ],
  "review_required": true
}
```

**Nguyên tắc thiết kế:**
- Bảng CHUẨN (CĐKT/KQKD/LCTT): dùng `ma_so` làm khoá, tra theo danh mục cố định (Thông tư 200/133) — không parse tự do
- Bảng KHÔNG chuẩn (thuyết minh, phụ lục): trả dạng `headers`/`rows` tổng quát
- `confidence` theo **từng trường**, không chỉ tổng thể
- `vi_tri` (bounding box + trang) — cho phép UI sau này click để đối chiếu ảnh gốc (dữ liệu này PaddleOCR/PP-Structure vốn đã có sẵn ở bước detect, chỉ cần giữ lại)
- `validation_flags` + `review_required`: lớp đối chiếu nghiệp vụ tự động — đây là giá trị cốt lõi khác biệt so với OCR thô, không phải phần phụ

### 9.1 JSON có phải là tối ưu? — chuẩn hoá & định dạng bổ sung

JSON vẫn là lựa chọn đúng cho **response chính** của API (dễ tích hợp mọi ngôn ngữ, khớp hệ sinh thái FastAPI/Pydantic sẵn có). Cái cần làm "khoa học hơn" không phải là thay JSON, mà là **chuẩn hoá cách dùng JSON** + **bổ sung định dạng chuyên ngành** cho đúng nhu cầu từng khách hàng:

1. **JSON Schema chính thức, versioned** — thêm field `schema_version` (semver) vào mọi response, publish schema trong `docs/schemas/`, dùng chính Pydantic model làm nguồn chân lý (validate cả lúc test lẫn runtime). Tránh tình trạng response "trôi" dần theo thời gian mà consumer (web app sau này) không biết.
2. **Tách layout khỏi từng field** — với bảng lớn (BCTC nhiều trang), lặp lại `vi_tri` ở mỗi dòng gây phình payload. Có thể đưa toạ độ vào một registry riêng (`layout: [{id, trang, x, y, w, h}]`), field chỉ giữ `layout_ref: id`. Tối ưu kích thước, vẫn giữ khả năng click-để-đối-chiếu.
3. **Không nhúng base64 cho ảnh/PDF trung gian** trong JSON (phình ~33%, không cache được) — nếu cần trả kèm ảnh, dùng presigned URL tạm thời với TTL ngắn, tự xoá theo đúng nguyên tắc Mục 10.
4. **Bổ sung (không thay thế) các chuẩn digitization/archival quốc tế** — liên quan trực tiếp tới khách hàng công chứng, vì Luật Công chứng 2024 yêu cầu số hoá + nộp vào CSDL công chứng thống nhất toàn quốc:
   - **ALTO XML** (Analyzed Layout and Text Object) — chuẩn lưu trữ số hoá dùng phổ biến ở thư viện/văn khố, mô tả layout + text + toạ độ tới cấp dòng/từ. Nhiều hệ thống lưu trữ của cơ quan nhà nước yêu cầu định dạng này khi bàn giao.
   - **PAGE XML** — bản kế thừa hiện đại hơn ALTO, hỗ trợ layout phức tạp, reading order, bảng — chuẩn phổ biến trong nghiên cứu/thi đấu OCR (ICDAR).
   - **hOCR** (HTML + CSS nhúng bounding box) — nhẹ, render thẳng trên trình duyệt để review nội bộ, nhưng không đủ chuẩn hoá cho mục đích lưu trữ pháp lý dài hạn.
   - Đề xuất cụ thể: thêm endpoint tuỳ chọn `GET /api/v1/jobs/{id}/export?format=alto|page|hocr`. Đây cũng là điểm khác biệt cạnh tranh — OCR thô thường chỉ trả text/JSON, không đáp ứng được yêu cầu nộp hồ sơ số hoá theo chuẩn của cơ quan quản lý.
5. **Sẵn sàng nâng cấp lên gRPC/Protobuf cho kênh nội bộ (nguyên tắc thiết kế xuyên suốt, đã chốt)** — JSON/REST vẫn là API công khai hướng ngoài (khách hàng/web app tích hợp), nhưng khi hệ thống lớn ra nhiều service nội bộ (worker ↔ web app, hoặc thêm service khác), kênh nội bộ sẽ chuyển sang gRPC/Protobuf để lợi băng thông + tốc độ. Để không phải viết lại khi nâng cấp, thiết kế ngay từ đầu theo hướng:
   - Giữ response schema **phẳng, kiểu dữ liệu rõ ràng, tên field ổn định** — tránh dict lồng sâu/tự do kiểu `dict[str, Any]`, vì cấu trúc này khó ánh xạ sang Protobuf message.
   - Tách rõ **domain model** (Pydantic — nguồn chân lý theo điểm 1 ở trên) khỏi **lớp serialize HTTP/JSON** — logic nghiệp vụ (OCR, extract, validate) không phụ thuộc trực tiếp vào format response, để sau này thêm gRPC service song song mà không đụng vào logic đó.
   - Khi đặt tên/thứ tự field trong schema JSON, cân nhắc luôn tính nhất quán với quy ước Protobuf (tên field không đổi ý nghĩa qua các version, chuẩn bị sẵn tinh thần đánh số field ổn định) để việc viết `.proto` sau này chỉ là ánh xạ 1-1, không phải thiết kế lại.

### 9.2 Hiệu suất & tốc độ xử lý

Máy chạy `ocr-engine` dùng CPU Intel thế hệ hybrid (i5-14500: 6 P-core × 2 luồng + 8 E-core × 1 luồng = 20 luồng) — điều này ảnh hưởng trực tiếp tới cách cấu hình worker/thread, không chỉ đơn giản là "có bao nhiêu luồng":

1. **Không tự pin process vào core theo index cứng** (`taskset -c`, `SetProcessAffinityMask`, `os.sched_setaffinity` với danh sách ID cụ thể). Đây là nguyên nhân của nhiều lỗi thực tế từng gặp — core index không đồng đều giữa P-core (2 luồng/core) và E-core (1 luồng/core), code giả định "mọi core như nhau" sẽ gán nhầm luồng nặng vào core yếu hoặc core đang bận, gây treo/chậm bất thường. Đây là **lỗi giả định của code, không phải lỗi hệ điều hành** — xảy ra được trên cả Linux lẫn Windows nếu code tự ghim core theo index.
2. **Giới hạn CPU bằng cgroup quota, không ghim core cứng** — đã áp dụng đúng hướng này trong `docker-compose.yml` (`deploy.resources.limits.cpus`): đây là "ngân sách thời gian CPU", kernel tự chọn core phù hợp (Linux CFS hybrid-aware từ nhân 5.18+/6.x), tránh hẳn lớp lỗi ở mục 1 — không cần và không nên tự ghim core trong code ứng dụng.
3. **Số worker process tune bằng benchmark thực tế, không suy từ số luồng lý thuyết** — bắt đầu thử 4-6 worker, đo throughput trên mẫu BCTC thật, tăng dần tới điểm throughput không tăng thêm (bão hoà do tranh chấp bộ nhớ/cache, không phải do "hết luồng đếm được").
4. **Tách queue theo loại việc**: `ocr-jobs` (CPU-bound: OCR/PP-Structure) tách khỏi `webhook-delivery` (I/O-bound: gọi callback, retry) — 1 webhook endpoint chậm/chết không được giữ worker OCR đang rảnh.
5. **Priority lane theo kích thước job**: hồ sơ CCCD/sổ đỏ (1-2 trang) đi queue riêng khỏi BCTC nhiều trang — job nhỏ không bị xếp sau job nặng.
6. **Model load 1 lần/worker process** — load ở module scope/worker init, không load lại trong hàm xử lý từng job (model load tốn vài giây, lặp lại mỗi job là lãng phí lớn).
7. **Tinh chỉnh số luồng nội bộ ONNX Runtime/OpenVINO (`intra_op_num_threads`) khớp số worker process chạy đồng thời** — nếu mỗi worker tự đặt full số luồng khả dụng, N worker sẽ giành CPU lẫn nhau (thrashing); set theo (tổng luồng cấp cho container) / (số worker process).
8. **Downsample DPI trước khi OCR** — scan gốc thường 300-600 DPI, OCR không cần vượt quá ~200-300 DPI; tối ưu tốc độ dễ nhất, hay bị bỏ qua.
9. **Batch inference nhiều trang trong 1 lần gọi model** (PP-OCRv5 hỗ trợ batch) thay vì loop từng trang.
10. **Timeout cứng theo từng bước pipeline** (OCR, PP-Structure, extract) — job kẹt không được giữ worker vô thời hạn.

### 9.3 Độ tin cậy & khả năng quan sát (reliability/observability)

- Retry có backoff cho cả lỗi xử lý tạm thời lẫn gọi webhook thất bại — dùng cơ chế `Retry` sẵn có của RQ, không tự viết lại
- Log dạng JSON có `job_id`/`tenant_id` xuyên suốt để trace 1 job qua nhiều dòng log — không lẫn giữa các job chạy song song
- Metrics tối thiểu: độ sâu từng queue, thời gian xử lý/job, tỷ lệ lỗi — biết khi nào cần tăng worker thay vì đoán (`docker compose up --scale worker=N`)
- Rate limit theo API key (token bucket) — bảo vệ năng lực máy đơn khỏi 1 tenant chiếm hết queue, bổ sung cho API4 (Mục 10.2, xem [security.md](security.md))

### 9.4 Quy trình vận hành API tổng quan (tổng hợp lại từ các mục trên)

#### 9.4.1 Cung cấp API (onboarding 1 tenant — làm 1 lần)

1. Ký hợp đồng dịch vụ với khách hàng — xác lập cơ sở pháp lý xử lý dữ liệu cá nhân hộ khách hàng (Mục 10.1)
2. Cấp cho tenant **2 secret khác nhau**, không dùng chung: `api_key` (tenant xác thực khi gọi job tới `ocr-engine`) và `tenant_secret` (tenant tự verify chữ ký webhook nhận về — chi tiết ở 9.4.3)
3. Tenant đăng ký trước **domain callback được phép** (Mục 10.2.1) — xác minh qua DNS TXT hoặc email admin; job của tenant chỉ được chọn domain trong danh sách này, không truyền URL tuỳ ý
4. Gắn `tenant_id` cố định cho tenant — mọi `job_id` (UUID không đoán được, Mục 10.2) tạo ra sau này đều thuộc về đúng 1 tenant
5. (Khi cần) cấu hình rate limit/quota riêng cho tenant đó (Mục 9.3)

#### 9.4.2 Sử dụng API (quy trình 1 job — lặp lại mỗi lần xử lý tài liệu)

```
Tenant                                  ocr-engine
  │                                          │
  │── POST /api/v1/jobs ───────────────────▶│  (file + doc_type + callback_url + api_key)
  │                                          │  1. Xác thực api_key → tenant_id
  │                                          │  2. Validate callback_url (SSRF-safe, Mục 10.2.1)
  │                                          │  3. Validate file (magic byte, size/trang, virus scan — Mục 10.4)
  │                                          │  4. Lưu file tạm (tmpfs), đẩy vào queue theo loại/kích thước (Mục 9.2)
  │◀── {job_id, status: "queued"} ──────────│
  │                                          │
  │                                    [Worker xử lý bất đồng bộ]
  │                                    - Tiền xử lý + OCR/PP-Structure
  │                                      hoặc field extraction theo loại giấy tờ (Mục 8.3-8.5)
  │                                    - Rule engine validate nghiệp vụ (Mục 8.6)
  │                                    - Xoá file gốc/ảnh trung gian ngay sau khi xong
  │                                          │
  │◀── webhook callback (kèm X-Signature) ──│  HOẶC tenant tự GET /api/v1/jobs/{id} (polling)
  │                                          │
  │  5. Verify chữ ký (9.4.3 bên dưới)
  │  6. Dedupe theo job_id (webhook là at-least-once, không phải exactly-once — Mục 4.1)
  │  7. Map kết quả vào hệ thống riêng của tenant
```

Vài điểm cần nhớ khi vận hành thật: nếu webhook gọi lỗi/timeout thì tự động retry có backoff (Mục 9.3), vẫn lỗi thì log cảnh báo chứ không âm thầm mất job; `schema_version` đi kèm mọi response (Mục 9.1) nên tenant cần kiểm tra field này thay vì giả định cấu trúc cố định mãi mãi; toàn bộ luồng trên áp dụng y hệt cho webapp lẫn bất kỳ bên thứ ba nào, không có luồng "đặc quyền" riêng (Mục 4.1, xem [architecture.md](architecture.md)).

#### 9.4.3 `tenant_secret` là gì, vì sao tách riêng khỏi `api_key`

**Mục đích:** `tenant_secret` dùng để `ocr-engine` **ký (sign)** payload webhook gửi đi (`X-Signature: HMAC-SHA256(body, tenant_secret)` — Mục 10.8), để tenant xác minh webhook nhận được đúng là từ `ocr-engine`, không bị giả mạo/sửa đổi giữa đường.

**Vì sao không dùng chung `api_key`:** hai secret bảo vệ hai chiều tin cậy khác nhau, nên tách để giảm thiệt hại nếu 1 trong 2 bị lộ:
- `api_key` chảy theo chiều tenant → ocr-engine (chứng minh tenant có quyền gọi job). Nếu lộ, kẻ tấn công gọi job giả mạo tenant đó — **không** giả mạo được webhook vì không biết `tenant_secret`.
- `tenant_secret` chảy theo chiều ocr-engine → tenant (chứng minh webhook đúng là ocr-engine gửi). Nếu lộ, kẻ tấn công có thể gửi webhook giả (dữ liệu OCR bịa đặt) tới hệ thống tenant — **không** gọi job giả mạo được vì không biết `api_key`.
- Gộp chung 1 secret cho cả 2 chiều nghĩa là lộ 1 lần = mất cả 2 khả năng phòng vệ — tách riêng là nguyên tắc chuẩn (tương tự publishable key vs webhook signing secret của Stripe).

**Sinh & lưu trữ:** sinh ngẫu nhiên phía `ocr-engine` lúc onboarding (đủ entropy, vd 32 byte trở lên — không cho tenant tự chọn chuỗi dễ đoán), hiển thị/gửi cho tenant **đúng 1 lần** qua kênh an toàn lúc cấp. **Khác với `api_key` (chỉ cần so sánh nên lưu băm một chiều được), `tenant_secret` không thể lưu dạng băm** — `ocr-engine` phải dùng lại chính giá trị gốc để tính `HMAC-SHA256(body, tenant_secret)` mỗi lần gửi webhook, mà băm một chiều thì không đảo ngược được. Thay vào đó: **mã hoá lúc lưu trữ (encrypt at rest)** bằng khoá đối xứng phía server (vd `cryptography.fernet`, khoá lưu ở biến môi trường tách biệt hoàn toàn khỏi git — mất khoá này đồng nghĩa mọi `tenant_secret` đã lưu không thể khôi phục, cần tính phương án sao lưu khoá riêng), chỉ giải mã trong bộ nhớ đúng khoảnh khắc ký webhook, không log ra file log kỹ thuật (đúng nguyên tắc Mục 10.5), và **không có API nào trả lại giá trị gốc sau lần hiển thị đầu tiên**.

**Rotation:** hỗ trợ đổi `tenant_secret` mà không gây gián đoạn — cấp secret mới, chấp nhận **song song cả secret cũ và mới** trong 1 khoảng thời gian chuyển tiếp (vd 7 ngày) để tenant kịp cập nhật phía họ, sau đó thu hồi secret cũ. Áp dụng cùng nguyên tắc rotation đã nêu chung cho API key (Mục 10.2).

**Vì sao chọn HMAC đối xứng (không phải chữ ký bất đối xứng)**: ở quy mô pilot, HMAC đối xứng (2 bên giữ cùng 1 secret) là lựa chọn thực dụng, giống Stripe/GitHub webhook cổ điển — đơn giản, đủ an toàn nếu bảo vệ secret đúng cách (rotation + không log). Chữ ký bất đối xứng (`ocr-engine` giữ private key ký, tenant chỉ cần public key để verify, không cần bảo vệ bí mật gì) an toàn hơn về mặt không cần chia sẻ bí mật, nhưng thêm độ phức tạp quản lý khoá — chưa cần thiết ở quy mô hiện tại, có thể nâng cấp sau nếu có khách hàng yêu cầu (vd cơ quan nhà nước với chuẩn bảo mật cao hơn — Mục 10.7).

### 9.5 Monitoring & alerting khi lên production (mới, chưa có trước đây)

**Stack tự host, không cần SaaS đắt tiền** — phù hợp quy mô 1 máy, 2 người, ngân sách nhỏ (Mục 11, xem [business.md](business.md)):

- **Prometheus + Grafana + Loki** ("PLG stack", mã nguồn mở, chạy thêm vài container ngay trong `docker-compose.yml`) — Prometheus thu metrics, Grafana làm dashboard, Loki gom log để tìm kiếm (thay vì `docker logs` thủ công từng container)
- Nguồn metrics: FastAPI (`prometheus-fastapi-instrumentator`), độ sâu từng RQ queue (`ocr-jobs`/`webhook-delivery` — Mục 9.2 đã tách), `redis_exporter`, `postgres_exporter`, `node_exporter` (CPU/RAM/đĩa của máy)

**Trước tiên: 2 chế độ kết nối khác nhau, ảnh hưởng trực tiếp tới kênh alerting nào thực sự khả dụng** — không giả định máy luôn có internet ổn định:

- **Chế độ nội bộ/không chắc có internet** — máy hiện tại đang nằm trong mạng nội bộ, kết nối ra ngoài có thể không ổn định hoặc bị chặn theo hướng cụ thể; đây là hiện trạng thực tế cần thiết kế cho, không phải trường hợp hiếm
- **Chế độ internet-facing** (bản dự định cung cấp ra internet sau này) — lúc đó mới có thể tin cậy vào dịch vụ bên thứ ba qua internet

**Nguyên tắc cốt lõi: alerting không được hardcode vào 1 dịch vụ/ứng dụng cụ thể** — Alertmanager (đi kèm Prometheus) hỗ trợ nhiều loại receiver cấu hình được (SMTP, webhook, Slack, PagerDuty...) qua file cấu hình, không qua code. Đổi kênh khi đổi môi trường triển khai chỉ là đổi config.

**Kênh alerting theo mức độ chắc chắn khả dụng (từ luôn có tới chỉ tiện lợi khi đủ điều kiện):**

1. **Luôn khả dụng, không cần internet: Grafana dashboard xem qua mạng nội bộ/VPN** — đây là mức nền bắt buộc có ở mọi chế độ triển khai. Nếu máy thực sự không có internet ra ngoài, đây là kênh chính: vận hành viên chủ động xem định kỳ, không có push tự động.
2. **SMTP email** — nếu máy có lối ra internet (hoặc dùng mail server nội bộ sẵn có, phổ biến ở môi trường ngân hàng/cơ quan nhà nước) thì ưu tiên hơn 1 ứng dụng nhắn tin cụ thể, vì SMTP là giao thức chuẩn phân tán qua nhiều nhà cung cấp, không phải điểm chặn tập trung duy nhất như 1 app riêng lẻ.
3. **SMS qua gateway trong nước** (vd eSMS, SpeedSMS) cho cảnh báo khẩn cấp khi cần báo tới điện thoại — chạy qua API HTTPS chuẩn, không phụ thuộc hạ tầng của 1 ứng dụng nhắn tin cụ thể.
4. **Telegram/Zalo OA — chỉ là kênh tiện lợi bổ sung khi máy internet-facing ổn định, không phải kênh bắt buộc/duy nhất.** Bạn nói đúng: Telegram từng bị chặn/giảm tốc ở một số ISP Việt Nam theo từng giai đoạn, và máy hiện tại chưa chắc có internet — đặt cược toàn bộ alerting vào riêng Telegram là rủi ro thật, không phải lý thuyết. Nếu muốn 1 kênh app nhắn tin, Zalo OA (dịch vụ trong nước, ít khả năng bị chặn diện rộng trong nước hơn) là lựa chọn thay thế đáng cân nhắc hơn Telegram cho riêng thị trường Việt Nam — nhưng vẫn chỉ nên là kênh phụ, không thay thế mục 1-2 ở trên.

**Giám sát từ bên ngoài (uptime check) — điều chỉnh theo chế độ kết nối, không phải lúc nào cũng là dịch vụ public:**

- Nếu máy chưa internet-facing: dùng 1 máy KHÁC trong cùng mạng nội bộ (không phải chính máy `ocr-engine`) ping định kỳ endpoint health — vẫn giữ nguyên tắc "hệ thống giám sát không được sập chung với máy nó giám sát", chỉ khác đối tượng ping là nội bộ thay vì public
- Khi đã internet-facing: có thể nâng cấp thêm dịch vụ heartbeat public bên ngoài (UptimeRobot/Better Uptime bản miễn phí) ping endpoint `/health` công khai, làm lớp bổ sung chứ không bắt buộc phải thay thế máy giám sát nội bộ
- Dù chế độ nào, Prometheus/Grafana chạy trên chính máy `ocr-engine` không được xem là đủ — đây là lớp "ai giám sát người giám sát", dễ bị quên vì có vẻ dư thừa nhưng chính là lớp phát hiện sự cố nghiêm trọng nhất (mất toàn bộ máy)

**Backup & khả năng phục hồi:** Postgres là nơi duy nhất lưu job metadata/audit trail (Mục 10.5) — máy chỉ có 1, không có redundancy. Cần `pg_dump` tự động định kỳ, lưu ra ngoài máy (cloud storage/VPS khác), và tự báo nếu job backup thất bại/không chạy — mất máy mà mất luôn audit trail là rủi ro thật với khách hàng công chứng cần truy vết.

**Log rotation:** Docker mặc định lưu log dạng `json-file` không giới hạn kích thước, có thể làm đầy đĩa nếu không cấu hình `max-size`/`max-file` — cần đặt giới hạn ngay từ `docker-compose.yml`, không đợi tới lúc đầy đĩa mới nhớ ra.

**Kỳ vọng với khách hàng pilot — nói rõ, không hứa quá:** hệ thống giám sát ở trên phục vụ đội ngũ vận hành tự biết sự cố, **không đồng nghĩa với SLA uptime chính thức** — với 1 máy duy nhất không có failover, nên nói rõ với khách hàng pilot đây là giai đoạn best-effort, không cam kết uptime %, đúng tinh thần minh bạch đã có ở Mục 2.2 (xây niềm tin bằng case study, không phải lời hứa quá mức).
