---
name: competition-gtm
description: "Cạnh tranh & go-to-market cho ocr-engine — không lấy CCCD làm mũi nhọn (eKYC đã bão hoà), rủi ro công chứng bị khoá bởi hệ thống tập trung cần xác minh sớm, moat là domain knowledge/data/quan hệ; thêm nhóm KH ISO 9001 do người dùng tự đề xuất"
metadata: 
  node_type: memory
  type: project
  originSessionId: 49bddbc6-5ce5-4f38-9e40-5c12e78ef8ed
  modified: 2026-07-26T03:06:33.474Z
---

Đã thêm Mục 2.2 vào `OCR_ENGINE_DESIGN.md` — khung cạnh tranh/GTM, cố tình không nêu tên công ty cụ thể vì chưa có dữ liệu thị trường đủ tin cậy.

**Các điểm chiến lược quan trọng nhất:**

1. **Đối thủ thật là quy trình thủ công hiện tại** (nhân viên gõ tay, chưa số hoá kịp trước hạn luật), không phải 1 vendor OCR khác — mọi so sánh giá trị nên lấy mốc này.
2. **Không lấy CCCD/MRZ làm sản phẩm mũi nhọn** — các nhà cung cấp eKYC Việt Nam phục vụ ngân hàng/fintech nhiều khả năng đã làm tốt phần này từ lâu (nhu cầu KYC ngân hàng có sẵn) — dễ đụng vùng bão hoà. Nên dồn lợi thế cạnh tranh vào BCTC + sổ đỏ + hợp đồng công chứng, nơi ít vendor chuyên biệt hoá hơn.
3. **Rủi ro chiến lược cần xác minh SỚM (trước khi code thêm cho công chứng)**: nếu CSDL công chứng thống nhất quốc gia áp đặt vendor/nền tảng số hoá tập trung từ Sở/Bộ Tư pháp, văn phòng công chứng lẻ có thể không có quyền tự chọn nhà cung cấp — có thể làm sụp toàn bộ luận điểm chọn công chứng là khách hàng #1 (Mục 2). Đã thêm vào Mục 13 checklist: xác minh với 1-2 văn phòng công chứng quen biết TRƯỚC Tuần 8-9 (Mục 12) khi bắt đầu code hợp đồng công chứng.
4. **GTM phải high-touch, không phải self-serve** — khách hàng mục tiêu không phải developer. Kênh: hội nghề nghiệp, danh sách công khai (Sở Tư pháp/cổng đăng ký DN), referral ấm — khớp nguyên tắc đã chốt ở Mục 1 (không dùng tệp khách hàng ngân hàng).
5. **Moat thật sự không phải "có OCR"** (ai cũng wrap được PaddleOCR) mà là: (a) kiến thức nghiệp vụ kế toán/tín dụng của người sáng lập để tinh chỉnh rule engine ([[validation-rule-engine]]) đúng thực tế, (b) golden dataset + ngưỡng confidence hiệu chỉnh dần theo thời gian (Mục 14), (c) quan hệ/niềm tin với hội nghề nghiệp.
6. **Land-and-expand theo đúng tiến độ roadmap** — không chào bán loại giấy tờ chưa build/test xong (Mục 12).
7. **Nhóm khách hàng bổ sung do người dùng tự đề xuất**: DN đang làm/duy trì ISO 9001 (không giới hạn ngành) — yêu cầu "kiểm soát thông tin dạng văn bản" của ISO tạo động lực số hoá hồ sơ giấy tương tự công chứng, nhưng tài liệu đa dạng hơn nên độ chuyên biệt hoá/moat thấp hơn, cạnh tranh trực tiếp hơn với OCR/document management tổng quát. Kênh referral riêng: đơn vị tư vấn ISO/tổ chức chứng nhận (người phát hiện nhu cầu qua gap analysis). Đã thêm vào Mục 2 (dòng 3) và Mục 2.2 của design doc — chưa đưa vào roadmap kỹ thuật (Mục 12), cần khảo sát cụ thể trước khi mở rộng phạm vi extractor sang loại tài liệu ISO (hồ sơ chất lượng, biên bản, checklist...).

**Why quan trọng phải nhớ:** khi bàn tiếp về chiến lược thương mại, không tự suy đoán/bịa tên đối thủ cụ thể ở Việt Nam — chỉ đưa khung phân loại + khuyến nghị xác minh thực tế, để người dùng tự kiểm chứng qua thị trường họ nắm rõ hơn tôi.
