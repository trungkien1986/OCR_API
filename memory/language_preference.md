---
name: language-preference
description: "Mọi tài liệu của dự án OCR_API_plan (design doc, memory, plan file) phải viết bằng tiếng Việt, kể cả plan file do EnterPlanMode tạo ra"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 49bddbc6-5ce5-4f38-9e40-5c12e78ef8ed
  modified: 2026-07-26T03:53:26.004Z
---

Viết tiếng Việt cho toàn bộ tài liệu thuộc dự án `OCR_API_plan` — design doc, memory, và **cả plan file do EnterPlanMode/ExitPlanMode tạo ra** (thuật ngữ kỹ thuật tiếng Anh giữ nguyên xen trong câu, như đã làm xuyên suốt `OCR_ENGINE_DESIGN.md`/`design/*.md`).

**Why:** Lần đầu viết plan file (Phase 1 "Tuần 1") bằng tiếng Anh theo mặc định của công cụ — người dùng yêu cầu dừng lại, việt hoá rồi mới cho tiếp ("việt hóa và lưu lại rồi mới làm nhé"). Toàn bộ phần còn lại của dự án (7 file `design/*.md`, tất cả memory) đều bằng tiếng Việt; plan file là ngoại lệ duy nhất từng bị viết sai ngôn ngữ.

**How to apply:** Khi dùng EnterPlanMode cho dự án này, viết nội dung file plan (`C:\Users\LaptopKien\.claude\plans\*.md`) bằng tiếng Việt ngay từ đầu, không đợi người dùng nhắc lại. Áp dụng tương tự cho bất kỳ tài liệu mới nào sinh ra cho dự án này (báo cáo, ghi chú, checklist).
