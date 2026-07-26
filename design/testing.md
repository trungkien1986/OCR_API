> Module của [OCR_ENGINE_DESIGN.md](../OCR_ENGINE_DESIGN.md) — chiến lược kiểm thử (golden dataset, chỉ số đo lường, regression gate, test phi chức năng). Số mục giữ nguyên như file gốc để không phá vỡ tham chiếu chéo.

## 14. Chiến lược kiểm thử (Testing Strategy)

### 14.1 Bộ dữ liệu chuẩn (golden dataset)

- Tuân thủ nguyên tắc Mục 1 (xem [business.md](business.md)): BCTC công khai + hồ sơ tự soạn giả lập — **không bao giờ dữ liệu thật**
- Có ground-truth đi kèm (giá trị đúng + bounding box + mã số) gán nhãn thủ công 1 lần, dùng làm baseline so sánh cho mọi lần thay đổi code sau này
- Bổ sung tập **edge-case cố ý đưa vào từ đầu, không phải hiếm gặp**: ảnh nghiêng, mờ, có mộc đỏ đè chữ số, nhiều cột, viết tay xen lẫn — đây là tình huống thực tế thường xuyên ở hồ sơ công chứng/tín dụng
- Cân nhắc dùng thư viện augmentation mô phỏng nhiễu scan thật (xoay, nhiễu, biến dạng nén) để mở rộng tập test tổng hợp mà không cần thêm dữ liệu thật

### 14.2 Chỉ số đo lường

- OCR mức ký tự: Character Error Rate (CER) / Word Error Rate (WER)
- Mức trường dữ liệu: % mã số chỉ tiêu trích đúng giá trị — khắt khe hơn CER, vì sai 1 chữ số coi như sai cả trường
- Mức bảng: % bảng được nhận diện đúng cấu trúc (không thiếu/gộp nhầm dòng)
- **Hiệu chỉnh độ tin cậy (confidence calibration)**: confidence mô hình báo 0.9 có thực sự tương ứng ~90% khả năng đúng không (vẽ reliability diagram) — không mặc định tin số confidence tự báo
- Độ chính xác của `validation_flags`: recall (bắt được bao nhiêu lỗi thật) và precision (bao nhiêu cảnh báo là dương tính giả) — đây là chỉ số quan trọng nhất vì là giá trị cốt lõi sản phẩm (nguyên tắc thiết kế ở Mục 9, xem [api.md](api.md))

### 14.3 Regression gate trong CI

- Chạy golden dataset qua toàn bộ pipeline ở mỗi lần đổi code OCR/extract/validate, so với baseline đã lưu — chặn merge nếu chỉ số tụt quá ngưỡng cho phép
- Benchmark PaddleOCR vs VietOCR (Mục 12 roadmap, xem [roadmap.md](roadmap.md)) dùng chung bộ chỉ số ở Mục 14.2 để quyết định bằng dữ liệu, không theo cảm tính

### 14.4 Vòng lặp học từ review thủ công

- Hồ sơ bị gắn `review_required=true` sau khi người kiểm tra thủ công → hồ sơ đó (ẩn danh, đúng nguyên tắc Mục 1) trở thành ca test mới bổ sung vào golden dataset — tránh lặp lại lỗi đã từng phát hiện

### 14.5 Test phi chức năng

- **Load test**: nhiều job nộp đồng thời, đo độ sâu queue/throughput thực tế dưới tải — dữ liệu đầu vào để tune số worker theo Mục 9.2 (benchmark thực tế, không suy diễn lý thuyết)
- **Soak test**: worker chạy liên tục nhiều giờ, theo dõi rò rỉ bộ nhớ (ONNX Runtime/PaddleOCR có tiền lệ rò rỉ session ở một số cấu hình)
- **Test bảo mật tự động**: fuzz input file upload, test case SSRF trên `callback_url` (Mục 10.2.1, xem [security.md](security.md)) nằm trong bộ test tự động chạy mỗi lần đổi code — không chỉ review thủ công 1 lần rồi thôi
