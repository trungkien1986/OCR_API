> Module của [OCR_ENGINE_DESIGN.md](../OCR_ENGINE_DESIGN.md) — pipeline xử lý 1 job, chiến lược trích xuất theo từng loại giấy tờ, rule engine validate nghiệp vụ. Số mục giữ nguyên như file gốc để không phá vỡ tham chiếu chéo.

## 8. Pipeline xử lý (1 job)

1. Nhận file (PDF/ảnh scan) + `doc_type` + `callback_url` → lưu tạm → trả `job_id` ngay
2. Worker: OCR toàn văn bản (PaddleOCR)
3. Nếu `doc_type = bctc`: chạy thêm PP-Structure nhận diện bảng → map theo **Mã số chỉ tiêu chuẩn (Thông tư 200/133)**
   Nếu `doc_type = tin_dung/cong_chung`: rule-based field extraction theo layout
4. Lớp **validate nghiệp vụ**: đối chiếu công thức đã biết trước (vd Mã số 270 = 100 + 200), đối chiếu chéo giữa các trường/trang
5. Trả kết quả qua webhook + **xoá file gốc và ảnh trung gian ngay sau khi trả kết quả thành công**

### 8.1 Tiền xử lý & phân loại — chi tiết kỹ thuật

- **PDF có text layer sẵn (không phải ảnh scan thuần)**: ưu tiên trích xuất trực tiếp từ text layer thay vì OCR — nhanh hơn và chính xác gần như tuyệt đối; chỉ chạy OCR khi không có text layer hoặc text layer rỗng/lỗi (PDF xuất từ máy tính vs PDF từ máy scan cần phân biệt ngay bước đầu, không mặc định mọi PDF đều phải OCR)
- **Deskew (chỉnh nghiêng) + khử nhiễu trước khi OCR** — hồ sơ công chứng/tín dụng thường chụp/scan nghiêng, có bóng, gấp mép; đây là bước tiền xử lý bắt buộc, không phải tuỳ chọn
- **Đối chiếu `doc_type` client khai với nội dung thực tế** bằng lớp phân loại nhẹ (không phải chạy OCR đầy đủ rồi mới biết sai) — nếu lệch, trả cảnh báo thay vì cắm đầu xử lý sai luồng trích xuất
- **Mộc/dấu đỏ công chứng đè lên chữ số hoặc chữ** là tình huống rất phổ biến ở hồ sơ công chứng/tín dụng thật (không phải edge-case hiếm) — cần benchmark riêng ảnh hưởng của dấu đỏ tới OCR, cân nhắc tách kênh màu đỏ trước khi OCR nếu ảnh hưởng đáng kể

### 8.2 Trích xuất bảng BCTC — xử lý đặc thù để đạt độ chính xác cao

- **Định dạng số kiểu Việt Nam**: dấu **chấm phân cách nghìn, phẩy phân cách thập phân** (ngược tiếng Anh), số âm thường viết trong ngoặc đơn `(x)` — parser số phải theo đúng quy ước này, không dùng parser mặc định kiểu Anh-Mỹ
- **Nhầm chữ số (0/8, 1/7, 3/8) là lỗi nghiêm trọng nhất** với dữ liệu tài chính vì sai lệch số tiền — lớp đối chiếu công thức đã biết trước (Mục 8 bước 4) là tuyến phòng thủ chính; nếu benchmark cho thấy tỷ lệ lỗi nhận diện số còn cao, cân nhắc thêm 1 lượt OCR thứ 2 chỉ trên vùng số để đối chiếu chéo
- **Tận dụng tên chỉ tiêu là danh mục đóng, hữu hạn** (Thông tư 133/200 đã có sẵn toàn bộ tên gọi chuẩn) — fuzzy-match tên chỉ tiêu OCR được với danh mục chuẩn thay vì tin nguyên văn OCR, tự sửa lỗi dấu tiếng Việt phổ biến (sắc/huyền/hỏi/ngã/nặng). Đây là tối ưu đặc thù nghiệp vụ mang lại độ chính xác cao hơn nhiều so với OCR tổng quát, vì phạm vi từ vựng đã biết trước và hữu hạn
- **Giới hạn đã biết của v1 với bảng không chuẩn** (phụ lục/thuyết minh): chỉ hỗ trợ header 1 dòng; header nhiều dòng/merged cell phức tạp hơn sẽ rơi vào `review_required=true` thay vì cố map sai — ghi nhận rõ giới hạn thay vì âm thầm suy diễn

**Trạng thái hiện tại (đã code, `extractors/bctc.py` + `ocr/`):** pipeline Bảng cân đối kế toán (Mẫu B01-DN, Thông tư 200) chạy đủ luồng preprocess (text layer/rasterize/deskew) → OCR (`lang="vi"`) → PP-StructureV3 → parse HTML bảng → fuzzy-match tên chỉ tiêu (`rapidfuzz`, ngưỡng 70) hoặc khớp trực tiếp mã số 3 chữ số → rule engine (`validation/`). CHƯA làm: KQKD/LCTT (chỉ CĐKT), ngưỡng confidence hiệu chỉnh theo Mục 14.2 (review_required v1 chỉ dựa vào "không nhận diện được bảng nào" HOẶC có rule lỗi), và chưa chạy qua Docker/máy production thật lần nào — xem `plans/phase2-bctc-ocr-pipeline.md`.

**Ghi chú quan trọng về `doc_type`:** taxonomy hiện tại (`tin_dung`, `cong_chung`) đang gộp nhiều loại giấy tờ có cấu trúc hoàn toàn khác nhau vào chung 1 nhóm. Cần tách nhỏ theo loại giấy tờ cụ thể — `cccd`, `so_do`, `hop_dong_cong_chung`, `to_trinh_tin_dung` (đã phản ánh ở cấu trúc thư mục Mục 7, xem [architecture.md](architecture.md)) — vì mỗi loại cần 1 chiến lược trích xuất khác nhau, trình bày ở 8.3-8.5 dưới đây.

### 8.3 Trích xuất CCCD/CMND — tận dụng MRZ & QR thay vì chỉ OCR tự do

- CCCD gắn chip (từ 2021) có **MRZ (Machine Readable Zone)** ở mặt sau — chuỗi ký tự chuẩn ICAO 9303 (giống hộ chiếu), có **check digit** (thuật toán mod-10 có trọng số) để tự kiểm tra đúng/sai. Ưu tiên đọc MRZ trước, chỉ dựa vào OCR text tự do khi MRZ không đọc được — nếu checksum MRZ khớp, độ tin cậy gần như tuyệt đối mà không cần OCR toàn bộ mặt trước.
- CCCD gắn chip cũng có **mã QR** ở mặt sau, mã hoá thông tin công dân dạng chuỗi có dấu phân cách — **giải mã QR (không phải OCR)** cho độ chính xác cao hơn hẳn so với đọc chữ in tự do.
- **Đối chiếu chéo OCR text (mặt trước: họ tên, ngày sinh, số CCCD) với dữ liệu giải mã từ MRZ/QR (mặt sau)** — áp dụng đúng nguyên lý `validation_flags` đã dùng cho BCTC (Mục 8 bước 4), chỉ khác nguồn đối chiếu là MRZ/QR thay vì công thức kế toán. Lệch giữa 2 nguồn → flag ngay, không cần đợi review thủ công mới phát hiện.
- Dữ liệu CCCD là dữ liệu cá nhân nhạy cảm bậc cao nhất trong toàn hệ thống (Mục 10.1, xem [security.md](security.md)) — không log bất kỳ phần nào của số CCCD/họ tên/địa chỉ, kể cả khi debug.

### 8.4 Trích xuất sổ đỏ/sổ hồng — theo version mẫu, không phải 1 layout cố định

- Mẫu Giấy chứng nhận QSDĐ đã đổi qua nhiều thời kỳ (sổ đỏ cũ, sổ hồng, mẫu 2009, mẫu theo Luật Đất đai 2024) — vị trí trường dữ liệu khác nhau giữa các mẫu. Cần bước **nhận diện phiên bản mẫu trước khi áp field-position**, giống cách BCTC nhận diện mã số theo danh mục chuẩn — không giả định chỉ có 1 layout duy nhất.
- Phần "sơ đồ thửa đất" là bản vẽ kỹ thuật (hình dạng + kích thước cạnh), không phải văn bản — nằm ngoài phạm vi OCR text extraction hợp lý cho v1; giữ lại ảnh vùng đó làm tham chiếu (`vi_tri`) thay vì cố ép ra dữ liệu có cấu trúc.
- Đối chiếu diện tích ghi bằng số với diện tích ghi bằng chữ (nếu có) trên cùng giấy tờ — cùng nguyên lý cross-check như số tiền BCTC.

### 8.5 Hợp đồng công chứng & tờ trình tín dụng — pattern-anchored + template theo tenant, không hardcode 1 mẫu

Đây là 2 loại **không có mẫu chuẩn quốc gia cố định** (khác hẳn CCCD/sổ đỏ): hợp đồng công chứng do các bên/luật sư soạn tự do theo từng vụ việc; tờ trình phê duyệt tín dụng do từng tổ chức tín dụng tự thiết kế mẫu riêng. Rule-based theo toạ độ cố định (như CCCD/sổ đỏ) **sẽ gãy ngay** khi đổi khách hàng/mẫu — cần chiến lược khác:

- **Trường bắt buộc theo Luật Công chứng** (số công chứng, quyển số, ngày công chứng, họ tên công chứng viên, tên tổ chức hành nghề công chứng) xuất hiện ở hầu hết văn bản công chứng theo đúng quy định pháp luật — đây là mục tiêu trích xuất có độ tin cậy cao nhất, dùng pattern-anchored (regex quanh từ khoá "Số công chứng:", "Quyển số:"...) chứ không phải toạ độ cố định
- Nội dung thân hợp đồng (điều khoản cụ thể từng vụ việc) chỉ trích theo kiểu tìm-từ-khoá/tóm tắt, **không cam kết trích xuất đầy đủ có cấu trúc** — ghi rõ giới hạn này thay vì cố ép ra dữ liệu không đáng tin
- **Tờ trình tín dụng**: vì mỗi tổ chức tín dụng có mẫu riêng, thiết kế cơ chế **template cấu hình theo tenant** (file YAML/JSON mô tả vùng/từ khoá từng trường, đọc từ thư mục `templates/` ở Mục 7) thay vì viết cứng 1 parser — giống mô hình các sản phẩm OCR hoá đơn/chứng từ thương mại (Nanonets, Rossum...), không giả định biết trước layout của khách hàng tương lai
- **Đối chiếu chéo giữa các giấy tờ trong cùng 1 hồ sơ** (nếu tờ trình + sổ đỏ đính kèm cùng job): giá trị tài sản đảm bảo/diện tích ghi trong tờ trình phải khớp dữ liệu trích từ sổ đỏ đính kèm — mở rộng nguyên lý `validation_flags` từ trong-1-tài-liệu (BCTC) sang giữa-nhiều-tài-liệu-trong-1-hồ-sơ

### 8.6 Lớp validate nghiệp vụ — rule engine cấu hình được, không hardcode if/else

`validation_flags`/`review_required` là giá trị cốt lõi của sản phẩm (nguyên tắc thiết kế Mục 9, xem [api.md](api.md)) — cần thiết kế nghiêm túc như 1 thành phần riêng, không phải vài dòng if/else rải rác trong từng extractor.

1. **Rule engine cấu hình (YAML/JSON), không hardcode** — mỗi rule định nghĩa `{rule_id, doc_type, fields_involved, expression, severity, message_template}`. Thêm/sửa rule nghiệp vụ (vd Thông tư sửa công thức) chỉ cần cập nhật file cấu hình, không sửa code — cùng triết lý với `templates/` ở Mục 8.5.
2. **4 nhóm rule theo nguồn đối chiếu** (đã dùng rải rác ở 8.2-8.5, formalize lại):
   - Công thức trong-1-tài-liệu (Mã số 270 = 100 + 200 — BCTC)
   - Đối chiếu 2 nguồn trên cùng giấy tờ (số vs chữ — sổ đỏ; OCR text vs MRZ/QR — CCCD)
   - Đối chiếu giữa nhiều giấy tờ trong cùng hồ sơ (tài sản đảm bảo tờ trình vs sổ đỏ đính kèm)
   - Kiểm tra hợp lý/định dạng đơn lẻ (ngày không ở tương lai, số công chứng đúng định dạng...)
3. **Severity 3 mức, định nghĩa rõ ràng** (thay vì chuỗi tự do):
   - `error`: sai logic/toán học chắc chắn (270 ≠ 100+200, checksum MRZ sai) → luôn ép `review_required=true`
   - `warning`: bất thường nhưng có thể vẫn hợp lệ (số liệu ngoài khoảng thường gặp) → gợi ý review, không ép buộc
   - `info`: ghi chú không ảnh hưởng quyết định (field confidence thấp nhưng không có nguồn đối chiếu để xác nhận đúng/sai)
4. **`review_required` là kết quả tổng hợp có công thức rõ ràng**, không phải quyết định ngầm định — `true` nếu: có bất kỳ rule `error`, HOẶC field nào có confidence dưới ngưỡng đã hiệu chỉnh (Mục 14.2, xem [testing.md](testing.md)), HOẶC gặp giới hạn đã biết của pipeline (mẫu sổ đỏ không nhận diện được, header bảng nhiều dòng...)
5. **`validation_flags` trả về có cấu trúc**, không chỉ chuỗi mô tả — bổ sung `rule_id`, `expected`, `actual`, `delta` bên cạnh `issue`/`severity` hiện có, để web app sau này highlight khác biệt trực tiếp thay vì phải parse chuỗi text
6. **Versioning cho bộ rule** — Thông tư có thể sửa đổi công thức theo thời gian; mỗi job lưu `rules_version` đã áp dụng (giống `schema_version` ở Mục 9.1) — phục vụ truy vết/audit (Mục 10.5), đặc biệt khi khách hàng công chứng cần biết hồ sơ được xử lý theo quy tắc nào
7. **Giới hạn cần nói rõ với khách hàng**: validate nghiệp vụ bắt được các loại sai lệch **đã biết trước** (công thức, đối chiếu 2 nguồn), không phải cam kết bắt được mọi lỗi OCR — tránh truyền thông kiểu "AI đã kiểm tra hết"
