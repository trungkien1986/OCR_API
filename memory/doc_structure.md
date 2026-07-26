---
name: doc-structure
description: "OCR_ENGINE_DESIGN.md đã tách thành index rút gọn + module design/*.md theo chủ đề — sửa nội dung chi tiết ở đúng module, không sửa lại vào file gốc"
metadata: 
  node_type: memory
  type: project
  originSessionId: 49bddbc6-5ce5-4f38-9e40-5c12e78ef8ed
  modified: 2026-07-26T03:17:34.489Z
---

Ngày 2026-07-26, `OCR_ENGINE_DESIGN.md` (từng dài 547 dòng) đã được quy hoạch lại thành **index rút gọn (~70 dòng)** + 7 file module trong `design/`:

- `design/business.md` — Mục 1, 2, 2.1, 2.2, 11 (bối cảnh, khách hàng, giá trị/định giá, cạnh tranh/GTM, ngân sách)
- `design/architecture.md` — Mục 3, 4, 4.1, 5, 5.1, 6, 7 (kiến trúc, ranh giới webapp, hạ tầng, tech stack, cấu trúc thư mục)
- `design/pipeline.md` — Mục 8, 8.1-8.6 (pipeline xử lý, trích xuất theo loại giấy tờ, rule engine validate)
- `design/api.md` — Mục 9, 9.1-9.4 (thiết kế API, hiệu suất, reliability, tenant_secret)
- `design/security.md` — Mục 10, 10.1-10.8 (bảo mật & tuân thủ)
- `design/roadmap.md` — Mục 12, 13 (roadmap + checklist việc cần chốt — **file thay đổi thường xuyên nhất**)
- `design/testing.md` — Mục 14 (chiến lược kiểm thử)

**Why:** file gốc quá dài (547 dòng, 14 mục + hàng chục mục con) sau nhiều vòng rà soát — user yêu cầu quy hoạch lại để dễ phát triển theo module và dễ đọc.

**Nguyên tắc quan trọng khi làm việc tiếp với tài liệu này:**
- Số mục (1, 2, 2.1, 8.6, 10.2.1...) **giữ nguyên xuyên suốt** giữa file gốc và các file module — không đánh số lại, để mọi tham chiếu chéo "Mục X" trong toàn bộ hệ thống (kể cả trong memory khác) vẫn đúng dù nội dung đã chuyển file.
- **Khi cần sửa/bổ sung nội dung chi tiết của 1 mục cụ thể → sửa trực tiếp trong file module tương ứng** (vd sửa Mục 8.3 → sửa `design/pipeline.md`), không sửa vào `OCR_ENGINE_DESIGN.md` (file gốc giờ chỉ là tóm tắt + link).
- Nếu một thay đổi đủ quan trọng để đổi tóm tắt ở file gốc (vd đổi quyết định cốt lõi), cập nhật cả 2 nơi: chi tiết ở module + dòng tóm tắt tương ứng ở `OCR_ENGINE_DESIGN.md`.
- File gốc có bảng "Bản đồ tài liệu" ở đầu — đó là nguồn tra cứu module nào chứa mục nào.
- Cấu trúc này chỉ tồn tại trong thư mục `C:\OCR_API_plan` (bản kế hoạch) — không nhầm với `docs/` bên trong `ocr-engine/` (thư mục code tương lai, Mục 7) vốn là tài liệu kỹ thuật của chính code, khác mục đích.
