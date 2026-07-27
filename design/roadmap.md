> Module của [OCR_ENGINE_DESIGN.md](../OCR_ENGINE_DESIGN.md) — roadmap kỹ thuật và các quyết định chưa chốt. File này thay đổi thường xuyên nhất trong toàn bộ tài liệu — cập nhật trạng thái tại đây khi có quyết định mới. Số mục giữ nguyên như file gốc để không phá vỡ tham chiếu chéo.

## 12. Roadmap kỹ thuật (cập nhật — kéo dài ~2 tuần so với bản gốc do bổ sung an toàn/kiểm thử từ đầu)

> Thời gian trước pilot tăng từ ~8 tuần lên ~10 tuần vì đưa bảo mật/hạ tầng vào đúng từ tuần 1 (thay vì làm sau), thêm CCCD/sổ đỏ/template tín dụng, và bắt đầu gán nhãn golden dataset sớm — đánh đổi hợp lý cho "tiêu chuẩn cao nhất từ đầu", không phải trì hoãn không lý do.

| Giai đoạn | Việc chính |
|---|---|
| Tuần 1 | ✅ Hạ tầng: `docker-compose.yml` (API+worker+Redis+Postgres), CI/CD đầy đủ (Mục 5.2 — xem [architecture.md](architecture.md): GitHub Actions + self-hosted runner + cổng duyệt thủ công), API key + tenant model, khung chống SSRF cho `callback_url` + ký HMAC webhook ngay từ đầu (Mục 10.2.1, 10.8 — xem [security.md](security.md)) — không phải phần thêm sau |
| Tuần 1-2 (song song) | 🔶 Golden dataset: mới có 2 BCTC công khai thật (HOSE/HNX, `tests/fixtures/bctc/`) làm hạt giống — CHƯA gán nhãn ground-truth, CHƯA có edge-case mộc đỏ/nghiêng/mờ (Mục 14.1, xem [testing.md](testing.md)) |
| Tuần 2-6 | ✅ (gộp, đi nhanh hơn dự kiến) OCR PaddleOCR (`lang="vi"`) + PP-StructureV3 nhận diện bảng + danh mục mã số **Thông tư 200** (đổi từ quyết định Thông tư 133 ban đầu — xem Mục 13 bên dưới) cho Bảng cân đối kế toán (Mẫu B01-DN) + parser số kiểu Việt Nam + rule engine validate cấu hình YAML (Mục 8.2, 8.6, xem [pipeline.md](pipeline.md)). CHƯA benchmark DPI/số luồng thật (Mục 9.2), CHƯA chạy qua Docker/production thật lần nào — xem `plans/phase2-bctc-ocr-pipeline.md` |
| Tuần 6-7 | ⬜ CCCD (MRZ/QR — Mục 8.3) + sổ đỏ (nhận diện version mẫu — Mục 8.4) — làm trước vì có mẫu chuẩn, ít biến động hơn giấy tờ tự do |
| Tuần 8-9 | ⬜ Hợp đồng công chứng (pattern-anchored) + template engine cho tờ trình tín dụng (Mục 8.5) |
| Tuần 9-10 | 🔶 Rule engine validate nghiệp vụ cấu hình được + `validation_flags` có cấu trúc (Mục 8.6) — bản v1 cho riêng BCTC đã xong sớm ở Tuần 2-6 ở trên, còn thiếu KQKD/LCTT + benchmark PaddleOCR vs VietOCR trên golden dataset (dùng chung bộ chỉ số Mục 14.2) |
| Tuần 10+ | ⬜ Regression gate CI dựa trên golden dataset (Mục 14.3), load/soak test (Mục 14.5) |
| Sau đó | ⬜ Pilot với 2-3 khách hàng công chứng/kế toán dịch vụ THẬT (ngoài hệ thống ngân hàng hiện tại) → mới bắt đầu `webapp` |

## 13. Việc cần chốt trước khi code (chưa quyết định)

- [ ] Đường dẫn/tên thư mục dự án mới
- [x] DB cho `ocr-engine`: **PostgreSQL** — JSONB khớp hướng JSON Schema (Mục 9.1), concurrency tốt hơn MySQL cho workload trạng thái job, đủ nhẹ chạy cùng máy pilot
- [x] Danh mục mã số: ~~Thông tư 133 làm chuẩn trước~~ → **đổi thành Thông tư 200 làm chuẩn trước** (Mẫu B01-DN) — lý do đổi: BCTC công khai HOSE/HNX dùng làm fixture/golden dataset thực tế đều lập theo Thông tư 200 (doanh nghiệp niêm yết), không phải Thông tư 133 (SME); ví dụ JSON ở [api.md](api.md) Mục 9 (mã số 100/270) cũng khớp Thông tư 200. Thông tư 133 (Mẫu B01a-DNN, mã số khác hẳn) sẽ thêm sau dưới dạng bảng tra riêng khi có fixture SME thật, dùng chung engine hiện có (`extractors/ma_so_200.py`, `validation/rules_bctc.yaml`)
- [ ] Nguồn BCTC công khai cụ thể sẽ dùng để test (HOSE/HNX/website DN nào)
- [ ] Xác nhận với tư vấn pháp lý văn bản hiện hành về bảo vệ dữ liệu cá nhân (Nghị định 13/2023/NĐ-CP hay luật thay thế mới hơn) trước khi pilot với dữ liệu CCCD/sổ đỏ thật
- [ ] Có cần endpoint export ALTO/PAGE XML ngay từ pilot đầu tiên (khách công chứng) hay để sau khi có yêu cầu cụ thể từ CSDL công chứng thống nhất
- [ ] Mô hình định giá cụ thể (đơn giá/hồ sơ hay gói thuê bao) + mức giá từng phân khúc (Mục 2.1, xem [business.md](business.md)) — cần customer discovery thực tế, không tự chốt bằng phân tích kỹ thuật
- [ ] Pilot 2-3 khách hàng đầu có tính phí hay miễn phí đổi case study (Mục 2.1) — quyết định kinh doanh, ảnh hưởng dòng tiền và cách tiếp cận bán hàng
- [ ] Xác minh với 1-2 văn phòng công chứng quen biết: có được tự chọn vendor số hoá hay bị ràng buộc theo hệ thống tập trung của Sở/Bộ Tư pháp (Mục 2.2) — làm TRƯỚC khi đầu tư code cho hợp đồng công chứng (Tuần 8-9 ở trên), ảnh hưởng trực tiếp tới việc công chứng có nên giữ vị trí khách hàng #1 (Mục 2) hay không
