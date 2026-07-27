# Phase 2 ("Tuần 2-6" gộp) — Pipeline OCR + trích xuất BCTC (Bảng cân đối kế toán) đầu tiên

## Bối cảnh

Tiếp nối Phase 1 (`plans/phase1-tuan1-ha-tang.md`, xem thêm [[cicd_pipeline]]): hạ tầng (API+worker+Redis+Postgres, CI/CD, tenant/API key, chống SSRF, ký HMAC webhook) đã xong, `workers/pipeline.py` chỉ là placeholder rỗng. Phase này thay placeholder bằng pipeline OCR thật đầu tiên, phạm vi hẹp có chủ đích: **chỉ `doc_type=bctc`, chỉ Bảng cân đối kế toán (Mẫu B01-DN)** — chưa đụng tới CCCD/sổ đỏ/công chứng/tín dụng (Tuần 6-9 theo `design/roadmap.md`), chưa đụng tới KQKD/LCTT.

## Các quyết định/thay đổi so với tài liệu gốc (quan trọng nhất)

1. **Đổi danh mục mã số: Thông tư 200 thay vì Thông tư 133 làm chuẩn đầu tiên.** `design/roadmap.md` Mục 13 trước đó chốt "Thông tư 133 trước vì khớp khách hàng đầu (SME)". Lý do đổi: BCTC công khai HOSE/HNX — nguồn thực tế duy nhất sẵn có để làm fixture/golden dataset ngay bây giờ — đều lập theo Thông tư 200 (doanh nghiệp niêm yết), không phải Thông tư 133. Ví dụ JSON ở `design/api.md` Mục 9 (mã số 100/270) cũng khớp đúng Thông tư 200. Đã cập nhật `design/roadmap.md` Mục 13. Thông tư 133 (Mẫu B01a-DNN, mã số khác hẳn) để sau, dùng chung engine hiện tại.
2. **Sửa 1 nhận định sai trong `design/architecture.md` Mục 6**: tài liệu cũ ghi "PP-OCRv5 hỗ trợ tiếng Việt native, 106 ngôn ngữ" — SAI. PP-OCRv5 (dòng model mới nhất của PaddleOCR) thực ra chỉ hỗ trợ 5 ngôn ngữ (Trung giản/phồn thể, pinyin, Anh, Nhật). Hỗ trợ tiếng Việt nằm ở dòng model đa ngôn ngữ khác của cùng thư viện PaddleOCR (`lang="vi"`, ~100+ ngôn ngữ) — vẫn cùng 1 thư viện/license, chỉ khác lựa chọn model. Đã sửa lại `architecture.md` và dùng đúng `lang="vi"` trong code (`ocr/engine.py`).
3. **PP-Structure → PP-StructureV3**: tên gọi hiện tại của dòng model đó trong PaddleOCR 3.x (`paddleocr==3.7.*`). `ocr/table.py` đọc kết quả qua HTML tái dựng bảng (`<table>...`) thay vì JSON nội bộ — output HTML ổn định qua các version hơn, tên field JSON nội bộ chưa có tài liệu chính thức đầy đủ tại thời điểm viết. **Rủi ro lớn nhất chưa được xác minh**: `_find_table_html()` dò theo vài tên field phổ biến (`html`/`pred_html`/`table_html`) thay vì 1 đường dẫn cố định — CẦN chạy thật qua Docker để xác nhận đúng field.
4. **Bake model PaddleOCR/PP-StructureV3 vào Docker image lúc build** (`Dockerfile`, trước `COPY . .` để tận dụng cache layer) — máy production chưa chắc có internet ổn định (đã ghi nhận ở `design/api.md` Mục 9.5), không được để tải lazy lúc job đầu tiên chạy.
5. **Tách marker `slow` trong pytest** (`pyproject.toml`: `addopts = "-m 'not slow'"`) — CI nhanh mặc định KHÔNG chạy OCR/PP-StructureV3 thật. Test wiring API/queue/webhook dùng fixture `mock_pipeline` (autouse, `tests/conftest.py`) stub `run_pipeline`; test OCR thật (`tests/test_bctc_extraction_slow.py`) gọi thẳng `extract_bctc()`, chạy thủ công bằng `pytest -m slow`. Đây là bước đầu của "Regression gate CI" (`design/testing.md` Mục 14.3) — CHƯA nối thành 1 job CI riêng chạy khi merge/nightly, việc đó vẫn thuộc Tuần 10+.
6. **`workers/pipeline.py` từ placeholder rỗng → dispatcher theo `doc_type`**: `_EXTRACTORS = {"bctc": extract_bctc}`; `doc_type` khác raise `NotImplementedError` rõ ràng (không âm thầm trả kết quả rỗng) — `workers/tasks.py` bắt lỗi này như mọi lỗi pipeline khác, đánh dấu job `failed`.

## Thiết kế các module mới

### `ocr/` — wrapper PaddleOCR/PP-StructureV3

- `engine.py`: `PaddleOCR(lang="vi", use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False)`, load 1 lần/worker process qua `@lru_cache(maxsize=1)` (không load lại mỗi job — `design/pipeline.md` Mục 9.2 điểm 6). `recognize_page()` trả `list[RecognizedLine]` (text, confidence, box).
- `preprocess.py`: `has_text_layer()` (PDF xuất từ máy tính vs scan thuần, ngưỡng `_MIN_CHARS_PER_PAGE=20` để loại watermark/số trang rác), `extract_text_layer()`, `rasterize_pdf()` (PyMuPDF, DPI hạ còn 200 — `Mục 9.2 điểm 8`), `deskew()` (OpenCV, `minAreaRect` + `warpAffine`, bỏ qua nếu lệch <0.1°).
- `table.py`: wrapper `PPStructureV3()`, cùng nguyên tắc cache 1 lần/process. `detect_tables_html()` trả list HTML bảng.

### `extractors/` — logic riêng cho `doc_type=bctc`

- `number_parser.py`: `parse_vn_number()` — dấu chấm phân cách nghìn, phẩy phân cách thập phân (ngược Anh-Mỹ), số âm trong ngoặc đơn `(x)`, ô trống/gạch ngang trả `None` (phân biệt với `0` thật).
- `ma_so_200.py`: `MA_SO_200` (dict mã số 3 chữ số → tên chỉ tiêu chuẩn, Thông tư 200 Mẫu B01-DN) + `SUBTOTAL_COMPONENTS` (mã số nào là tổng của mã số nào — nguồn cho rule engine dựng công thức cộng dồn tự động, không liệt kê tay trong YAML). Giới hạn v1 ghi rõ trong docstring: bỏ qua mã số có hậu tố chữ (411a/411b...) và vài mục hiếm (323/339/340).
- `bctc.py`: `extract_bctc(file_path)` — ghép toàn bộ luồng: preprocess → OCR (nếu không có text layer) → PP-StructureV3 mỗi trang → parse HTML bảng (`_TableRowParser`, dùng `html.parser` chuẩn thư viện) → mỗi dòng bảng: khớp mã số trực tiếp (regex 3 chữ số có trong `MA_SO_200`) hoặc fuzzy-match tên chỉ tiêu (`rapidfuzz.process.extractOne`, `token_sort_ratio`, ngưỡng `_NAME_MATCH_CUTOFF=70`) → lấy số cuối kỳ/đầu kỳ từ các ô còn lại → rule engine → `review_required` = không nhận diện được bảng nào HOẶC có rule `error`.

### `validation/` — rule engine cấu hình YAML (mới, đúng nguyên tắc [[validation_rule_engine]])

- `engine.py`: chỉ hỗ trợ 2 dạng biểu thức an toàn bằng regex (KHÔNG `eval()` chuỗi tuỳ ý): `sum(a,b,c) == target` và `a == b`. Sai lệch trong ngưỡng `_TOLERANCE=1.0` (làm tròn kế toán) không tính là lỗi. `load_rules(path, doc_type)` lọc rule theo `doc_type` từ file YAML.
- `rules_bctc.yaml`: 7 rule cho Bảng cân đối kế toán — 6 công thức cộng dồn (100/200/270/300/400/440) + 1 đối chiếu chéo cơ bản nhất (270 == 440, Tổng tài sản = Tổng nguồn vốn). `rules_version: "1.0.0-tt200-cdkt"` lưu sẵn cho audit trail sau này (Mục 8.6 điểm 6).

## File cũ đã sửa

- `workers/pipeline.py`, `workers/tasks.py`: `run_placeholder_pipeline` → `run_pipeline`, dispatcher theo `doc_type`.
- `tests/conftest.py`: thêm fixture `mock_pipeline` (autouse) — test nào cần giả lập lỗi pipeline (`test_storage_cleanup.py`) tự `monkeypatch` đè lại trong thân test, chạy sau fixture này nên vẫn có hiệu lực.
- `Dockerfile`: bake model (mục 4 ở trên).
- `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`: marker `slow`; thêm `paddlepaddle==3.3.*`, `paddleocr[doc-parser]==3.7.*`, `pymupdf==1.28.*`, `pyyaml==6.*`, `rapidfuzz==3.*`, `types-PyYAML==6.*`.
- `.gitignore`: thêm `ThuVien/` — cache offline gói pip (wheel Linux/Python 3.11, paddlepaddle/paddleocr rất nặng), tự tải lại được bằng `pip download`, không commit vì kích thước lớn.
- `design/architecture.md`, `design/roadmap.md`, `design/pipeline.md`, `design/testing.md`: cập nhật theo các mục ở trên (xem diff kèm theo).

## Test

- `tests/test_number_parser.py`, `tests/test_ma_so_200.py`, `tests/test_validation_engine.py`: unit test thuần, không cần model — chạy trong CI nhanh mặc định.
- `tests/test_bctc_extraction_slow.py` (đánh dấu `slow`): chạy `extract_bctc()` thật trên 2 fixture ở `tests/fixtures/bctc/` (`duong_quang_ngai_q1_2025.pdf`, `vtc_telecom_q3_2025.pdf`), assert có nhận diện được mã số 270 (Tổng cộng tài sản). KHÔNG chạy trong CI mặc định, chạy thủ công `pytest -m slow`.
- Test wiring cũ (`test_storage_cleanup.py`...) cập nhật theo tên hàm mới (`run_pipeline`), vẫn dùng `mock_pipeline` stub — không tự dùng OCR thật.

## Khoảng trống còn lại đã biết, CHƯA làm ở phase này

- **Chưa chạy qua Docker/máy production thật lần nào** — rủi ro lớn nhất là `ocr/table.py::_find_table_html()` dò field JSON theo phỏng đoán tên phổ biến, cần xác minh field thật khi build image lần đầu.
- **Chưa benchmark DPI/số luồng** (`design/api.md` Mục 9.2) — `DEFAULT_OCR_DPI=200` là số chọn theo tài liệu, chưa đo thực tế trên máy đích.
- **Chưa gán nhãn ground-truth** cho 2 fixture BCTC đã có — test `slow` hiện tại chỉ assert "có nhận diện được mã số 270", chưa so khớp giá trị chính xác từng mã số (CER/WER, % mã số đúng — Mục 14.2).
- **Chưa có KQKD (Báo cáo kết quả kinh doanh)/LCTT (Lưu chuyển tiền tệ)** — chỉ Bảng cân đối kế toán.
- **`review_required` v1 đơn giản hơn thiết kế đầy đủ ở `pipeline.md` Mục 8.6 điểm 4** — chưa áp dụng ngưỡng confidence đã hiệu chỉnh (cần golden dataset/reliability diagram trước).
- **Chưa benchmark PaddleOCR vs VietOCR** — vẫn đúng lịch Tuần 9-10 theo roadmap, PaddleOCR chỉ là lựa chọn mặc định tạm thời.

## Kiểm chứng đã làm / còn thiếu

- Đã chạy: `pytest -q` (bộ nhanh, không có `slow`) — pass, không đụng model thật.
- Còn thiếu (cần làm trước khi coi phase này "xong" theo đúng tinh thần Mục 14 testing.md): `pytest -m slow` với model thật cài đủ (`pip install -r requirements.txt`, tốn thời gian tải model lần đầu), build thử `Dockerfile` để xác nhận bước bake model không lỗi và `_find_table_html()` tìm đúng field.
