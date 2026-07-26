---
name: field-extraction-strategy
description: "Chiến lược trích xuất trường dữ liệu khác nhau theo loại giấy tờ — CCCD dùng MRZ/QR, sổ đỏ theo version mẫu, hợp đồng công chứng/tờ trình tín dụng dùng pattern-anchored + template theo tenant"
metadata: 
  node_type: memory
  type: project
  originSessionId: 49bddbc6-5ce5-4f38-9e40-5c12e78ef8ed
  modified: 2026-07-26T02:37:21.967Z
---

Quyết định kiến trúc cho `ocr-engine`: **không dùng 1 chiến lược field-extraction duy nhất cho mọi giấy tờ**. `doc_type` ban đầu (`tin_dung`, `cong_chung`) gộp nhiều loại giấy tờ có cấu trúc khác nhau — đã tách nhỏ thành `cccd`, `so_do`, `hop_dong_cong_chung`, `to_trinh_tin_dung` (mỗi loại 1 extractor riêng). Xem `OCR_ENGINE_DESIGN.md` Mục 8.3-8.5.

**Why:** Mẫu nhà nước chuẩn hoá (CCCD, sổ đỏ) và giấy tờ tự do/theo tổ chức riêng (hợp đồng công chứng, tờ trình tín dụng) có đặc điểm hoàn toàn khác nhau — rule-based theo toạ độ cố định chỉ đúng cho loại đầu, sẽ gãy ngay với loại sau khi đổi khách hàng/mẫu.

**How to apply:**
- **CCCD/CMND**: ưu tiên đọc **MRZ** (Machine Readable Zone, chuẩn ICAO 9303, có check digit mod-10 tự kiểm tra) và **mã QR** ở mặt sau (CCCD gắn chip từ 2021) thay vì chỉ OCR text tự do — độ tin cậy cao hơn hẳn. Đối chiếu chéo OCR mặt trước với dữ liệu giải mã MRZ/QR mặt sau, dùng làm `validation_flags` giống cách BCTC đối chiếu công thức kế toán.
- **Sổ đỏ/sổ hồng**: có nhiều version mẫu qua các thời kỳ (sổ đỏ cũ, sổ hồng, mẫu 2009, mẫu theo Luật Đất đai 2024) — phải nhận diện version trước khi áp field-position, không giả định 1 layout cố định.
- **Hợp đồng công chứng**: không có mẫu quốc gia cố định — dùng pattern-anchored (regex quanh từ khoá) cho các trường bắt buộc theo Luật Công chứng (số công chứng, quyển số, ngày, công chứng viên...), không cam kết trích đầy đủ nội dung thân hợp đồng.
- **Tờ trình tín dụng**: mỗi tổ chức tín dụng có mẫu riêng — dùng cơ chế **template cấu hình theo tenant** (YAML/JSON mô tả vùng/từ khoá), không hardcode 1 parser cứng, giống mô hình SaaS OCR chứng từ thương mại (Nanonets, Rossum).
- Dữ liệu CCCD là dữ liệu cá nhân nhạy cảm bậc cao nhất — không log bất kỳ phần nào (số CCCD, họ tên, địa chỉ) kể cả khi debug.
- Liên quan [[grpc-protobuf-readiness]] — schema field-extraction output cũng nên giữ phẳng/ổn định theo cùng nguyên tắc.
