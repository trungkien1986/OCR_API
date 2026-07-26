# OCR Engine — Thiết kế tổng quan dự án

> Tài liệu tổng hợp toàn bộ quyết định đã thống nhất qua các buổi thảo luận. Dùng làm tài liệu gốc khi bắt đầu code trong thư mục dự án riêng (KHÔNG đặt trong repo BankingReport của ngân hàng).
>
> **Đã quy hoạch lại (2026-07-26): đây là bản rút gọn (index).** Chi tiết đầy đủ nằm trong `design/*.md`. File này giữ đúng bản chất "cốt lõi" — mỗi phần chỉ tóm tắt quyết định quan trọng nhất; mọi lý do/chi tiết kỹ thuật/số liệu đều ở file module tương ứng. Số mục (1, 2, 2.1...) giữ nguyên xuyên suốt toàn bộ tài liệu (cả ở đây lẫn trong `design/*.md`) để tham chiếu chéo không bị vỡ khi tách file.

---

## Bản đồ tài liệu

| Mục | Nội dung | File chi tiết |
|---|---|---|
| 1, 2, 2.1, 2.2, 11 | Bối cảnh, khách hàng, giá trị/định giá, cạnh tranh/GTM, ngân sách | [design/business.md](design/business.md) |
| 3, 4, 4.1, 5, 5.1, 6, 7 | Kiến trúc tổng thể, ranh giới webapp, phần cứng/hạ tầng, tech stack, cấu trúc thư mục | [design/architecture.md](design/architecture.md) |
| 8, 8.1-8.6 | Pipeline xử lý, trích xuất theo từng loại giấy tờ, rule engine validate nghiệp vụ | [design/pipeline.md](design/pipeline.md) |
| 9, 9.1-9.4 | Thiết kế API, chuẩn hoá định dạng, hiệu suất, reliability, quy trình vận hành | [design/api.md](design/api.md) |
| 10, 10.1-10.8 | Bảo mật & tuân thủ dữ liệu | [design/security.md](design/security.md) |
| 12, 13 | Roadmap kỹ thuật + việc cần chốt (checklist còn mở) | [design/roadmap.md](design/roadmap.md) |
| 14 | Chiến lược kiểm thử (testing strategy) | [design/testing.md](design/testing.md) |

Hạ tầng đã dựng sẵn ở thư mục gốc: `docker-compose.yml`, `Dockerfile`, `requirements.txt`, `.env.example` (xem [architecture.md](design/architecture.md) Mục 5.1). Ghi chú/quyết định lâu dài nằm ở `memory/` (không phải nội dung thiết kế, xem README riêng nếu có).

---

## 1. Bối cảnh (chi tiết: [business.md](design/business.md))

Dự án cá nhân, tách biệt hoàn toàn khỏi công việc ngân hàng hiện tại. **Không được vi phạm**: không dùng dữ liệu/khách hàng ngân hàng thật kể cả để test, code clean-room, kiểm tra hợp đồng lao động trước khi thương mại hoá.

## 2. Khách hàng & giá trị (chi tiết: [business.md](design/business.md))

- Ưu tiên: (1) văn phòng công chứng — Luật Công chứng 2024 bắt buộc số hoá, (2) SME/kế toán dịch vụ, (3) DN làm ISO 9001 (cơ hội song song), (4) Sở ban ngành (năm 2+)
- Bán **lớp validate nghiệp vụ + đối chiếu chuẩn** (MRZ/QR, ALTO/XML) — không bán OCR thô, đây mới là lợi thế cạnh tranh thật
- Tính phí theo đơn vị "hồ sơ"; mức giá cụ thể còn mở, cần customer discovery, không tự bịa số
- Rủi ro cần xác minh sớm: công chứng có bị khoá vendor bởi hệ thống CSDL tập trung quốc gia không (ảnh hưởng thứ tự ưu tiên khách hàng)

## 3-7. Kiến trúc & hạ tầng (chi tiết: [architecture.md](design/architecture.md))

- Giai đoạn 1: chỉ `ocr-engine`, webapp làm sau — nhưng giữ nguyên tắc "không cửa sau": webapp là khách hàng #1 như bất kỳ ai, mỗi khách hàng cuối = 1 tenant riêng
- `ocr-engine` không lưu trữ dữ liệu lâu dài, giao tiếp với webapp/bên thứ ba qua API + webhook
- Hạ tầng: Ubuntu Server + Docker Compose (API + worker + Redis + Postgres), không dùng Windows Service, không tự pin CPU core theo index (i5-14500 là CPU hybrid P/E-core — dùng cgroup quota)
- CI/CD: GitHub (repo private) + Actions — CI nhanh (lint/test/scan) mỗi PR, regression gate golden dataset khi merge `main`, CD qua **self-hosted runner ngay trên máy `ocr-engine`** với **cổng duyệt thủ công** trước khi deploy thật (chưa auto-deploy hoàn toàn ở giai đoạn pilot)
- Stack: FastAPI + RQ + PaddleOCR PP-OCRv5/PP-Structure

## 8. Pipeline xử lý (chi tiết: [pipeline.md](design/pipeline.md))

- 5 bước: nhận file → OCR → trích xuất theo loại giấy tờ → validate nghiệp vụ → trả kết quả + xoá file ngay
- Mỗi loại giấy tờ 1 chiến lược riêng: BCTC (mã số Thông tư + parser số kiểu VN), CCCD (ưu tiên MRZ/QR), sổ đỏ (theo version mẫu), hợp đồng công chứng/tờ trình tín dụng (pattern-anchored + template theo tenant, không hardcode)
- Validate nghiệp vụ (`validation_flags`/`review_required`) là **rule engine cấu hình YAML/JSON**, không hardcode if/else — đây là giá trị cốt lõi của sản phẩm

## 9. API (chi tiết: [api.md](design/api.md))

- JSON là response chính, có `schema_version`; thiết kế sẵn sàng nâng cấp gRPC/Protobuf cho kênh nội bộ sau này
- Tenant có **2 secret riêng biệt**: `api_key` (gọi job) và `tenant_secret` (ký/verify webhook) — lộ 1 cái không mất khả năng phòng vệ của cái kia
- Chống SSRF qua `callback_url` bằng domain allowlist đăng ký trước + validate IP + pin IP khi gọi thật
- Webhook là at-least-once — consumer phải tự dedupe theo `job_id`
- Monitoring/alerting production: Prometheus+Grafana+Loki tự host; **không hardcode kênh cảnh báo vào Telegram** — máy hiện chưa chắc có internet ổn định và Telegram từng bị chặn/giảm tốc ở VN, nên Grafana dashboard nội bộ là mức nền luôn khả dụng, SMTP/SMS gateway trong nước ưu tiên hơn app nhắn tin cụ thể, Telegram/Zalo chỉ là kênh phụ khi internet-facing ổn định; có uptime check độc lập với máy production (máy sập thì hệ thống giám sát nội bộ cũng sập theo); backup Postgres ra ngoài máy — pilot là best-effort, không hứa SLA uptime chính thức

## 10. Bảo mật (chi tiết: [security.md](design/security.md))

- Tuân thủ Nghị định 13/2023/NĐ-CP (bảo vệ dữ liệu cá nhân) — **cần xác nhận pháp lý trước pilot**, rủi ro cao hơn rủi ro kỹ thuật
- OWASP API Security Top 10 (2023), TLS 1.3 tối thiểu, input hardening (magic byte, virus scan, chống decompression bomb), audit trail tách biệt khỏi log kỹ thuật, quét lỗ hổng chuỗi cung ứng phần mềm/model AI

## 11. Ngân sách (chi tiết: [business.md](design/business.md))

**~35-70 triệu VNĐ** (2 người góp 50-50, không tính lương) — gồm cả tư vấn pháp lý (tách riêng, rủi ro cao nhất) và gán nhãn golden dataset (bắt buộc từ đầu, không còn tuỳ chọn "nếu fine-tune sau").

## 12-13. Roadmap & việc cần chốt (chi tiết: [roadmap.md](design/roadmap.md))

~10 tuần trước pilot (tăng từ 8 tuần vì đưa bảo mật/testing vào từ đầu thay vì làm sau). Còn nhiều quyết định mở — xem checklist đầy đủ trong file, đáng chú ý nhất: xác nhận pháp lý bảo vệ dữ liệu cá nhân, và xác minh rủi ro khoá vendor ở công chứng (Mục 2.2) trước khi đầu tư code cho hợp đồng công chứng.

## 14. Chiến lược kiểm thử (chi tiết: [testing.md](design/testing.md))

Golden dataset (kèm edge-case mộc đỏ/nghiêng/mờ) bắt buộc từ đầu, đo CER/field-accuracy/**hiệu chỉnh độ tin cậy**/precision-recall của `validation_flags`, regression gate chặn merge trong CI.
