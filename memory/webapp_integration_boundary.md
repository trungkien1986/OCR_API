---
name: webapp-integration-boundary
description: "Nguyên tắc ranh giới ocr-engine ↔ webapp/tích hợp tương lai — webapp là khách hàng #1 không có cửa sau, tenant theo từng khách hàng cuối, webhook at-least-once"
metadata: 
  node_type: memory
  type: project
  originSessionId: 49bddbc6-5ce5-4f38-9e40-5c12e78ef8ed
  modified: 2026-07-26T04:04:56.273Z
---

Quyết định kiến trúc cho `ocr-engine` liên quan tới webapp (làm sau, chưa code — Mục 3) và tích hợp bên thứ ba tương lai. Xem `OCR_ENGINE_DESIGN.md` Mục 4.1.

**Why:** `ocr-engine` được thiết kế để bán như dịch vụ API độc lập cho nhiều mục đích (Mục 4), không chỉ phục vụ riêng webapp — các quyết định dưới đây giữ cho khả năng đó không bị khoá chặt bởi giả định "chỉ có webapp gọi".

**How to apply:**
- **Webapp không có cửa sau** — khi xây, webapp gọi API qua đúng API key/tenant như khách hàng thứ ba, không bypass xác thực.
- **Tenant = từng khách hàng cuối** (văn phòng công chứng, kế toán dịch vụ), không phải "webapp = 1 tenant đại diện tất cả" — để bên thứ ba (phần mềm kế toán, CSDL công chứng quốc gia) có thể tích hợp trực tiếp không cần qua webapp.
- **Webhook là at-least-once** — mọi consumer phải tự dedupe theo `job_id`; đã chuẩn bị sẵn snippet verify chữ ký (`hmac.compare_digest`, không dùng `==`) để consumer tương lai dùng ngay, tránh tự implement sai.
- **`tenant_secret` tách riêng khỏi `api_key`** (chi tiết Mục 9.4.3): `api_key` chảy chiều tenant→ocr-engine (xác thực gọi job), `tenant_secret` chảy chiều ocr-engine→tenant (ký webhook để tenant verify nguồn gốc) — lộ 1 cái không kéo theo mất khả năng phòng vệ của cái kia. Sinh ngẫu nhiên lúc onboarding, hiển thị đúng 1 lần. **Sửa lỗi đã phát hiện lúc code Phase 1**: không thể lưu `tenant_secret` dạng hash một chiều như `api_key` (vì ocr-engine cần giá trị gốc để tính HMAC mỗi lần ký webhook) — phải **mã hoá lúc lưu trữ (encrypt at rest, vd Fernet)**, chỉ giải mã trong bộ nhớ lúc ký, không API nào trả lại giá trị gốc sau lần đầu. Hỗ trợ rotation song song (secret cũ+mới trong thời gian chuyển tiếp). Chọn HMAC đối xứng (không phải chữ ký bất đối xứng) vì đủ dùng ở quy mô pilot, có thể nâng cấp sau nếu khách hàng yêu cầu cao hơn (Mục 10.7).
- **Chính sách deprecation API** — khi có consumer thật đầu tiên phụ thuộc `/api/v1/`, breaking change phải báo trước vài tháng + chạy song song version mới.
- Ranh giới data controller (dữ liệu cá nhân) giữa `ocr-engine` và webapp sẽ cần xác định lại khi webapp bắt đầu lưu trữ lâu dài — ghi nhận, chưa giải quyết ngay.
- Liên quan [[grpc-protobuf-readiness]] — dù kênh nội bộ sau này chuyển gRPC, vẫn phải giữ đúng ranh giới tenant/auth, không biến thành "đường tắt tin cậy ngầm" giữa webapp và ocr-engine.
