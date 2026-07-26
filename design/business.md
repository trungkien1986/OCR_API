> Module của [OCR_ENGINE_DESIGN.md](../OCR_ENGINE_DESIGN.md) — bối cảnh, khách hàng, giá trị/định giá, cạnh tranh/GTM, ngân sách. Số mục giữ nguyên như file gốc để không phá vỡ tham chiếu chéo.

## 1. Bối cảnh & nguyên tắc bắt buộc

Dự án cá nhân, độc lập hoàn toàn với công việc ngân hàng hiện tại. Các nguyên tắc **không được vi phạm**:

- **KHÔNG** dùng tệp khách hàng, dữ liệu nghiệp vụ, BCTC/hồ sơ tín dụng thật của ngân hàng đang làm việc — kể cả để test.
- **KHÔNG** dùng chi nhánh đang công tác làm nơi pilot.
- Dữ liệu test: báo cáo tài chính **công khai** của doanh nghiệp niêm yết, hồ sơ tự soạn giả lập (số liệu hư cấu).
- Code viết lại từ đầu (clean-room), chỉ tái dùng *kỹ thuật/pattern* đã học được, không copy code/IP của ngân hàng.
- Kiểm tra hợp đồng lao động (điều khoản cấm cạnh tranh/IP) trước khi thương mại hoá.
- Kênh tiếp cận khách hàng: danh sách công khai (Sở Tư pháp, cổng đăng ký DN), hội nghề nghiệp, referral — **không** dùng tệp khách hàng ngân hàng.

## 2. Mục tiêu & đối tượng khách hàng (thứ tự ưu tiên)

| Thứ tự | Đối tượng | Lý do |
|---|---|---|
| 1 | **Văn phòng công chứng** | Luật Công chứng 2024 (hiệu lực 1/7/2025) bắt buộc số hoá + CSDL công chứng thống nhất toàn quốc — nhu cầu thật, đang diễn ra. ~1.300 tổ chức cả nước. |
| 2 | **SME / kế toán dịch vụ** | Đối chiếu sao kê ngân hàng đa ngân hàng — lợi thế chuyên môn riêng, ít đối thủ. |
| 3 (song song, cơ hội mở rộng) | **DN đang làm/duy trì ISO (9001 và tương tự), không giới hạn ngành** | Yêu cầu "kiểm soát thông tin dạng văn bản" của ISO thường buộc số hoá hồ sơ giấy tồn đọng + cần audit trail — có động lực tuân thủ giống công chứng, nhưng loại tài liệu đa dạng hơn (không giới hạn BCTC/CCCD/sổ đỏ) nên độ chuyên biệt hoá thấp hơn, cạnh tranh trực tiếp hơn với OCR/document management tổng quát (xem Mục 2.2) |
| 4 (năm 2 trở đi) | Sở ban ngành, trường công | Rào cản đấu thầu + chứng nhận an toàn thông tin cao, chu kỳ bán hàng dài — không phải nhóm khởi động. |

Loại tài liệu xử lý: CCCD/CMND, sổ đỏ/sổ hồng, hợp đồng công chứng, **báo cáo tài chính (BCTC)**, **hồ sơ phê duyệt tín dụng** — tất cả dạng file scan. Với nhóm ISO (dòng 3), phạm vi tài liệu có thể mở rộng hơn nữa (hồ sơ chất lượng, biên bản, checklist...) — **chưa đưa vào roadmap kỹ thuật hiện tại** (Mục 12, xem [roadmap.md](roadmap.md)), cần khảo sát cụ thể trước khi mở rộng phạm vi extractor.

### 2.1 Giá trị & định giá dịch vụ (khung đề xuất — số cụ thể cần chốt qua customer discovery thực tế, không tự bịa số)

**Giá trị cốt lõi bán cho khách hàng — không phải OCR thô:**

- OCR text nhận diện đơn thuần đã là hàng hoá phổ thông (Google/AWS Document AI, PaddleOCR đều làm được) — khách hàng không trả giá cao chỉ vì "đọc được chữ". Giá trị thật nằm ở lớp phía sau OCR, vốn đã xác định xuyên suốt tài liệu này:
  1. **Lớp validate nghiệp vụ tự động** (`validation_flags`/rule engine — Mục 8.6, xem [pipeline.md](pipeline.md)) — giảm thời gian rà soát thủ công + bắt lỗi số liệu mà OCR thô không tự biết là sai
  2. **Đối chiếu chuẩn có sẵn** (MRZ/QR cho CCCD — Mục 8.3; số vs chữ cho sổ đỏ — Mục 8.4) — độ tin cậy cao hơn hẳn OCR tổng quát vì tận dụng cấu trúc đã được chuẩn hoá sẵn của giấy tờ
  3. **Xuất theo chuẩn số hoá quốc tế** (ALTO/PAGE XML — Mục 9.1, xem [api.md](api.md)) — đáp ứng trực tiếp yêu cầu CSDL công chứng thống nhất của Luật Công chứng 2024, đối thủ OCR thô không có
- **Đóng gói giá nên phản ánh đúng thứ tự giá trị này** — cân nhắc tách 2 tier: "OCR thô" (rẻ, gần giá hàng hoá phổ thông) vs "OCR + validate nghiệp vụ + audit trail" (giá cao hơn rõ rệt) — vì tier thứ 2 mới là lợi thế cạnh tranh thật; định giá ngang bằng 2 tier là bỏ phí đòn bẩy khác biệt hoá

**Định giá theo phân khúc (thứ tự ưu tiên theo Mục 2):**

- **Công chứng**: giá trị = tuân thủ bắt buộc (Luật Công chứng 2024 không phải nhu cầu tuỳ chọn) + tiết kiệm thời gian số hoá hồ sơ tồn đọng → willingness-to-pay cao hơn, nhưng thị trường hữu hạn (~1.300 tổ chức) nên ARPU/tổ chức cần đủ cao để bù chi phí bán hàng dài (chu kỳ bán hàng B2B chuyên môn thường chậm)
- **Kế toán dịch vụ/SME**: giá trị = giảm giờ công đối chiếu sao kê đa ngân hàng + giảm sai sót nhập liệu BCTC → phân khúc nhạy giá hơn, nhưng số lượng khách hàng tiềm năng lớn hơn nhiều lần công chứng
- **Sở ban ngành/trường công** (năm 2+): thường qua đấu thầu/hợp đồng năm, không phải self-serve pricing — chưa cần thiết kế giá cho giai đoạn này (đúng nguyên tắc Mục 2 — không phải nhóm khởi động)

**Đơn vị tính phí — theo "hồ sơ", không phải "trang" hay "API call":**

- Khách hàng mục tiêu (công chứng viên, kế toán dịch vụ) tư duy theo đơn vị nghiệp vụ ("1 bộ hồ sơ", "1 bộ BCTC"), không phải "1 trang" hay "1 lần gọi API" — đơn vị tính phí nên khớp cách khách hàng nghĩ, dù bên trong hệ thống vẫn đo theo trang/job để tính chi phí vận hành thực tế
- Gợi ý cấu trúc: gói thuê bao tháng kèm số hồ sơ nhất định + phụ phí khi vượt hạn mức — dễ dự trù ngân sách cho văn phòng nhỏ hơn trả theo từng lần dùng rời rạc
- Đo lường mức dùng để tính phụ phí **không cần thêm hạ tầng gì mới** — đã có sẵn `tenant_id` + job hoàn thành lưu trong PostgreSQL (Mục 13, xem [roadmap.md](roadmap.md)), chỉ cần truy vấn theo kỳ tính phí

**Giá pilot — cần chốt rõ trước khi gặp khách hàng đầu tiên, không nên mặc định:**

- Pilot 2-3 khách hàng đầu (Mục 12) miễn phí/giảm giá đổi lấy phản hồi + quyền dùng làm case study, hay tính phí ngay từ đầu? Đây là **quyết định kinh doanh của bạn**, không phải điều kỹ thuật rút ra được — ảnh hưởng trực tiếp dòng tiền và cách tiếp cận bán hàng ban đầu, nên chốt trước khi tiếp xúc khách hàng pilot đầu tiên
- Trước khi chốt mức giá thương mại chính thức: cần dữ liệu thực tế qua customer discovery (khách hàng hiện đang trả bao nhiêu cho nhân sự nhập liệu thủ công hoặc dịch vụ số hoá hiện có, nếu có) — không nên chốt số cụ thể chỉ dựa vào ước tính lý thuyết một chiều

**Chưa cần tự động hoá billing** (đúng tinh thần không build trước nhu cầu, xuyên suốt tài liệu này): ở quy mô pilot 2-3 khách hàng, lên hoá đơn thủ công dựa trên số job hoàn thành/tenant là đủ; tự động hoá billing (Stripe metered billing...) chỉ đáng làm khi đã có doanh thu lặp lại ổn định, không phải việc của giai đoạn hiện tại.

### 2.2 Cạnh tranh & Go-to-market

**Đối thủ thật sự cần đánh bại trước tiên là quy trình thủ công hiện tại, không phải 1 công ty khác:**

- Với SME/kế toán dịch vụ: đối thủ số 1 là nhân viên tự gõ tay từ file scan — mọi so sánh giá trị (Mục 2.1) nên lấy mốc này làm chuẩn, không phải so với 1 sản phẩm OCR khác
- Với công chứng: đối thủ là tình trạng "chưa số hoá kịp" trước hạn luật định — áp lực tuân thủ tạo GTM angle tự nhiên ("giúp tuân thủ đúng hạn"), khác hẳn thông điệp OCR chung chung

**3 nhóm đối thủ gián tiếp cần khảo sát thực tế trước khi định vị** (cố tình không nêu tên công ty cụ thể ở đây vì chưa có dữ liệu thị trường đủ tin cậy tại thời điểm viết tài liệu — cần tự khảo sát, không suy đoán):

1. **Cloud OCR đa dụng** (Google Document AI, AWS Textract, Azure Form Recognizer...) — mạnh về OCR/extract tổng quát, nhưng không có sẵn: đối chiếu theo Thông tư 200/133, xử lý MRZ/QR CCCD Việt Nam, export ALTO/PAGE cho công chứng — đúng khoảng trống Mục 2.1 đã xác định
2. **Nhà cung cấp eKYC Việt Nam** (thường phục vụ ngân hàng/fintech) — nhiều khả năng **đã làm tốt phần CCCD/MRZ** vì đây là nhu cầu KYC ngân hàng đã có từ lâu. Cảnh báo quan trọng: **không nên lấy CCCD làm sản phẩm mũi nhọn** vì dễ đụng vùng đã bão hoà bởi các nhà cung cấp eKYC hiện có — nên định vị mũi nhọn ở BCTC + sổ đỏ + hợp đồng công chứng, nơi ít vendor chuyên biệt hoá hơn
3. **Vendor số hoá phục vụ riêng ngành công chứng/lưu trữ nhà nước** — **rủi ro chiến lược cần xác minh sớm**: nếu CSDL công chứng thống nhất quốc gia áp đặt vendor/nền tảng số hoá tập trung từ trên xuống, văn phòng công chứng lẻ có thể **không có quyền tự chọn nhà cung cấp**. Cần hỏi thẳng 1-2 văn phòng công chứng quen biết câu này TRƯỚC khi đầu tư nhiều tuần code cho hợp đồng công chứng (Mục 12, Tuần 8-9) — tránh xây xong rồi mới phát hiện thị trường đã bị khoá từ trên xuống

**Go-to-market — kênh phù hợp với nguồn lực thực tế (2 người làm ngoài giờ, ngân sách đi lại 5-10 triệu — Mục 11):**

- **Không phải self-serve API signup** — khách hàng mục tiêu (công chứng viên, kế toán dịch vụ) không phải developer tự tìm API để tích hợp; cần bán trực tiếp/high-touch, không kỳ vọng khách tự đăng ký qua trang web
- Kênh chính giữ nguyên như đã chốt ở Mục 1: hội nghề nghiệp (hội công chứng viên, hội kế toán/kiểm toán), danh sách công khai (Sở Tư pháp, cổng đăng ký DN), referral
- **Kênh bổ sung cho nhóm ISO** (Mục 2, dòng 3): đơn vị tư vấn ISO và tổ chức chứng nhận — các DN chuẩn bị audit ISO 9001 thường thuê tư vấn làm gap analysis, tư vấn là người phát hiện ra nhu cầu số hoá hồ sơ giấy và có thể giới thiệu công cụ; đây là kênh referral khác hẳn hội nghề nghiệp công chứng/kế toán, cần khảo sát riêng, chưa vội đầu tư nhiều thời gian vào kênh này song song với 2 kênh chính khi nguồn lực còn hạn chế (2 người, ngân sách đi lại nhỏ)
- **Rào cản niềm tin ban đầu**: 2 người làm side-project bán dịch vụ xử lý giấy tờ pháp lý/tài chính nhạy cảm cho văn phòng chuyên nghiệp — nên tìm khách hàng pilot đầu tiên qua mối quan hệ quen biết/giới thiệu ấm (warm intro) thay vì tiếp cận lạnh, để có case study/testimonial làm bàn đạp cho khách hàng thứ 2-3
- **Land-and-expand theo đúng tiến độ kỹ thuật** (Mục 12) — không chào bán loại giấy tờ chưa build/test xong; thứ tự chào bán nên đi theo đúng thứ tự roadmap (BCTC trước, CCCD/sổ đỏ, rồi mới tới công chứng/tín dụng), không hứa trước những gì chưa có

**Lợi thế cạnh tranh thật sự bền vững (moat) — không nằm ở việc "có OCR":**

- Bất kỳ ai cũng wrap được PaddleOCR thành API — công nghệ lõi không phải rào cản cạnh tranh
- Rào cản thật sự: (1) **kiến thức nghiệp vụ kế toán/tín dụng ngân hàng của người sáng lập** để tinh chỉnh rule engine (Mục 8.6) đúng thực tế nghiệp vụ — vendor thuần công nghệ khó copy nhanh; (2) **golden dataset + ngưỡng confidence được hiệu chỉnh dần qua thời gian** (Mục 14, xem [testing.md](testing.md)) — càng dùng càng chính xác hơn, đối thủ vào sau không có sẵn; (3) **quan hệ/niềm tin với hội nghề nghiệp** — khó sao chép bằng tiền hay công nghệ

## 11. Ngân sách (đã thống nhất, cập nhật theo phạm vi mở rộng)

| Khoản mục | Ước tính |
|---|---|
| Server + GPU (nếu mua thêm sau, không bắt buộc MVP) | 0 (dùng máy i5-14500 hiện có) |
| Công cụ/API dự phòng | 5-10 triệu |
| Đăng ký pháp nhân + kế toán ban đầu | 5-10 triệu |
| **Tư vấn pháp lý** (rà soát hợp đồng lao động — Mục 1; xác nhận nghĩa vụ bảo vệ dữ liệu cá nhân — Mục 10.1/13) | 5-10 triệu — *mới tách riêng*, trước đây ẩn trong "Dự phòng", nay tách rõ vì đây là rủi ro cao nhất của dự án |
| Đi lại/gặp khách hàng pilot | 5-10 triệu |
| Gắn nhãn dữ liệu cho golden dataset (Mục 14.1) | 5-15 triệu — *không còn là "nếu fine-tune sau"*: cần ngay từ đầu để làm regression test (Mục 14.3), không phụ thuộc việc có fine-tune model hay không |
| Dự phòng | 10-15 triệu |
| **Tổng** | **~35-70 triệu** (dev thứ 2 góp sức 50-50, không tính lương) |
