---
name: validation-rule-engine
description: "Lớp validate nghiệp vụ (validation_flags/review_required) thiết kế thành rule engine cấu hình YAML/JSON, không hardcode if/else"
metadata: 
  node_type: memory
  type: project
  originSessionId: 49bddbc6-5ce5-4f38-9e40-5c12e78ef8ed
  modified: 2026-07-26T02:42:02.076Z
---

Quyết định kiến trúc cho `ocr-engine`: lớp validate nghiệp vụ (`validation_flags`, `review_required` — giá trị cốt lõi của sản phẩm) phải là một **rule engine cấu hình được** (YAML/JSON: `{rule_id, doc_type, fields_involved, expression, severity, message_template}`), không phải if/else hardcode rải rác trong từng extractor. Xem `OCR_ENGINE_DESIGN.md` Mục 8.6.

**Why:** Công thức nghiệp vụ (Thông tư kế toán, quy định công chứng) có thể thay đổi theo thời gian; rule engine cho phép sửa/thêm rule bằng cấu hình, không cần sửa code — cùng triết lý với `templates/` dùng cho tờ trình tín dụng ([[field-extraction-strategy]]). Ngoài ra `validation_flags`/`review_required` là chỉ số được đo lường trực tiếp (precision/recall — Mục 14.2), nên cần rule có `rule_id` để truy vết rule nào gây false positive/negative.

**How to apply:**
- 4 nhóm rule theo nguồn đối chiếu: công thức trong-1-tài-liệu, đối chiếu 2 nguồn cùng giấy tờ (số vs chữ, OCR vs MRZ/QR), đối chiếu giữa nhiều giấy tờ trong hồ sơ, kiểm tra định dạng/hợp lý đơn lẻ.
- Severity 3 mức rõ ràng: `error` (luôn ép review), `warning` (gợi ý review), `info` (không ép).
- `review_required` là công thức tổng hợp rõ ràng (có rule error HOẶC confidence dưới ngưỡng đã hiệu chỉnh HOẶC gặp giới hạn pipeline đã biết), không phải quyết định ngầm định.
- `validation_flags` trả về có cấu trúc (`rule_id`, `expected`, `actual`, `delta`), không chỉ chuỗi mô tả.
- Rule set có version (`rules_version` lưu theo từng job) để audit/truy vết khi quy định thay đổi.
- Giới hạn cần nói rõ với khách hàng: validate bắt sai lệch đã biết trước, không cam kết bắt mọi lỗi OCR.
