---
name: pricing-value-framework
description: "Khung định giá dịch vụ ocr-engine — bán lớp validate nghiệp vụ chứ không phải OCR thô, tính phí theo hồ sơ; số giá cụ thể vẫn còn bỏ ngỏ"
metadata: 
  node_type: memory
  type: project
  originSessionId: 49bddbc6-5ce5-4f38-9e40-5c12e78ef8ed
  modified: 2026-07-26T02:58:46.932Z
---

Đã thêm khung (framework) định giá vào `OCR_ENGINE_DESIGN.md` Mục 2.1 — đây là khung tư duy, **không phải số giá cụ thể đã chốt**.

**Nội dung chính đã thống nhất về nguyên tắc:**
- Giá trị bán cho khách hàng KHÔNG phải OCR text thô (hàng hoá phổ thông) mà là lớp phía sau: validate nghiệp vụ tự động ([[validation-rule-engine]]), đối chiếu chuẩn MRZ/QR/số-chữ ([[field-extraction-strategy]]), export ALTO/PAGE XML cho công chứng.
- Nên tách 2 tier giá (OCR thô rẻ vs OCR+validate đắt hơn rõ rệt) thay vì định giá ngang bằng.
- Đơn vị tính phí nên là "hồ sơ" (khớp tư duy khách hàng công chứng/kế toán), không phải "trang" hay "API call" — dù đo lường nội bộ vẫn theo trang/job.
- Đo lường mức dùng để tính phí không cần hạ tầng mới — dùng luôn `tenant_id` + job hoàn thành trong PostgreSQL.
- Chưa cần tự động hoá billing ở quy mô pilot — lên hoá đơn thủ công là đủ.

**Còn bỏ ngỏ, KHÔNG tự chốt** (đã ghi vào Mục 13 checklist của design doc):
- Mức giá cụ thể (VNĐ/hồ sơ hay gói thuê bao) từng phân khúc — cần customer discovery thực tế (khách hàng hiện trả bao nhiêu cho nhập liệu thủ công/dịch vụ số hoá hiện có), không có đủ dữ liệu thị trường đáng tin để tự đưa ra con số.
- Pilot 2-3 khách hàng đầu tính phí hay miễn phí đổi case study — quyết định kinh doanh của người dùng, không phải điều rút ra được từ phân tích kỹ thuật.

**Why quan trọng phải ghi nhớ:** khi thảo luận tiếp về giá, không tự đưa ra con số VNĐ cụ thể (không có cơ sở dữ liệu thị trường đáng tin cậy) — chỉ nên đưa khung/câu hỏi cần trả lời qua customer discovery, để người dùng tự quyết dựa trên thực tế thị trường họ nắm được.
