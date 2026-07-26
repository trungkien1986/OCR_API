> Module của [OCR_ENGINE_DESIGN.md](../OCR_ENGINE_DESIGN.md) — bảo mật & tuân thủ dữ liệu, cập nhật theo tiêu chuẩn hiện hành. Số mục giữ nguyên như file gốc để không phá vỡ tham chiếu chéo.

## 10. Bảo mật & tuân thủ dữ liệu (cập nhật theo tiêu chuẩn hiện hành, rà soát 2026)

### 10.1 Khung pháp lý bảo vệ dữ liệu cá nhân — **bắt buộc**, không phải tuỳ chọn

CCCD/CMND, sổ đỏ, tình trạng tài chính (BCTC/hồ sơ tín dụng) đều là **dữ liệu cá nhân**, một phần là **dữ liệu cá nhân nhạy cảm** theo Nghị định 13/2023/NĐ-CP (và văn bản luật kế thừa/thay thế nếu đã có hiệu lực — **cần xác nhận lại với tư vấn pháp lý tại thời điểm code**, đây là rủi ro pháp lý cao hơn rủi ro kỹ thuật). Hệ quả kỹ thuật cần thiết kế sẵn:

- Có cơ sở pháp lý xử lý rõ ràng (hợp đồng dịch vụ ký với văn phòng công chứng/kế toán — bên xử lý hộ, không phải chủ thể dữ liệu)
- Thời gian lưu trữ **tối thiểu cần thiết** — khớp đúng nguyên tắc đã chốt "xoá file gốc + ảnh trung gian ngay sau khi trả kết quả" (Mục 8) — giữ nguyên, đây là thiết kế đúng hướng
- Có khả năng phản hồi/xoá theo yêu cầu chủ thể dữ liệu nếu về sau có lưu job metadata (Mục 13, xem [roadmap.md](roadmap.md))
- Quy trình thông báo sự cố lộ dữ liệu trong 72 giờ nếu có DPIA/ĐTNĐLDLC áp dụng ở quy mô lớn hơn pilot

### 10.2 OWASP API Security Top 10 (bản 2023, chuẩn hiện hành) — áp dụng cụ thể

- **API4 Unrestricted Resource Consumption**: giới hạn kích thước file, số trang, timeout/CPU per job — máy đơn không GPU dễ bị treo bởi 1 PDF nhiều trang hoặc file nén ác ý
- **API7 SSRF**: `callback_url` do client tự khai là điểm hở SSRF kinh điển — thiết kế chống cụ thể ở Mục 10.2.1 bên dưới
- **API2 Broken Authentication**: API key tĩnh chỉ là bước khởi đầu (đã ghi ở bản trước) — khi có khách hàng thật đầu tiên, nâng cấp lên HMAC request signing hoặc mTLS, không dừng ở Bearer token trần
- **API1/API3 Broken Object (Property) Level Authorization**: mỗi `job_id` gắn `tenant_id`, kiểm tra quyền truy vấn kết quả; dùng UUID không đoán được cho `job_id`, không dùng ID tăng dần

#### 10.2.1 Thiết kế chống SSRF cho `callback_url` (đã chốt)

Không tin `callback_url` client gửi trong request tạo job — client có thể trỏ vào `169.254.169.254` (cloud metadata), `127.0.0.1`, hoặc dải mạng nội bộ của chính máy `ocr-engine`/Redis. Áp dụng đồng thời các lớp phòng vệ sau (defense in depth — không dựa vào 1 lớp duy nhất):

1. **Đăng ký domain trước, không nhận URL tự do mỗi job** — khi cấp API key cho tenant, tenant đăng ký sẵn 1-vài domain callback được phép (qua kênh riêng, xác minh quyền sở hữu domain — vd. đặt DNS TXT record hoặc xác nhận qua email admin). Job request chỉ được chọn trong danh sách đã đăng ký, không được truyền URL tuỳ ý. Đây là lớp phòng vệ chính — mạnh hơn nhiều so với "validate URL lúc gọi".
2. **Chặn cứng theo scheme/IP tại thời điểm validate**:
   - Chỉ chấp nhận scheme `https://`
   - Từ chối nếu host là địa chỉ IP literal (không phải domain)
   - Resolve DNS của domain, từ chối nếu bất kỳ IP trả về thuộc dải private/reserved: `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16` (kể cả `169.254.169.254` — cloud metadata), `::1`, `fc00::/7`
3. **Chống DNS rebinding (TOCTOU)** — domain có thể resolve ra IP public lúc validate rồi đổi sang IP nội bộ lúc thực sự gọi webhook. Khắc phục: resolve 1 lần, validate IP, rồi **pin đúng IP đó** khi mở kết nối HTTP thật (không để HTTP client tự resolve lại DNS lần 2).
4. **Không follow redirect tự động** khi gọi webhook (`allow_redirects=False`), hoặc nếu bắt buộc theo redirect thì phải validate lại IP đích ở mỗi hop y hệt bước 2.
5. **Egress firewall ở tầng hạ tầng** (defense in depth, phòng trường hợp bug ở tầng ứng dụng) — worker gọi webhook nên chạy trong network namespace/container có rule chặn outbound tới toàn bộ dải IP private, chỉ cho phép ra Internet công khai
6. **Timeout ngắn + giới hạn số lần retry** cho lệnh gọi webhook, log lại và cảnh báo khi có request bị từ chối do nghi ngờ SSRF (dấu hiệu dò quét)

```python
import ipaddress, socket
from urllib.parse import urlparse

BLOCKED_NETS = [ipaddress.ip_network(n) for n in (
    "127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
    "169.254.0.0/16", "::1/128", "fc00::/7",
)]

def resolve_safe_callback(url: str, allowed_domains: set[str]) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("callback_url phải dùng https")
    if parsed.hostname not in allowed_domains:
        raise ValueError("domain chưa được tenant đăng ký")
    infos = socket.getaddrinfo(parsed.hostname, 443, proto=socket.IPPROTO_TCP)
    ip = infos[0][4][0]
    if any(ipaddress.ip_address(ip) in net for net in BLOCKED_NETS):
        raise ValueError("callback_url trỏ vào dải mạng nội bộ — từ chối")
    return ip  # pin IP này khi mở kết nối thật, không resolve lại
```

### 10.3 Mã hoá & vận chuyển

- TLS 1.3 tối thiểu cho mọi kết nối API; nếu bắt buộc tương thích ngược thì tối thiểu TLS 1.2 với cipher suite AEAD-only, tắt hẳn TLS 1.0/1.1
- Mã hoá at-rest (AES-256) cho file tạm và payload trong Redis queue — dù xoá nhanh, ảnh scan CCCD/sổ đỏ vẫn tồn tại vài giây–phút trên đĩa/swap, là bề mặt tấn công thực tế (disk forensics)
- Redis: bật `requirepass`/ACL, không expose ra ngoài mạng nội bộ của máy chủ, cân nhắc TLS cho kết nối Redis nếu payload nhạy cảm

### 10.4 Input hardening

- Xác thực file bằng magic byte, không tin theo đuôi file client khai
- Giới hạn kích thước + số trang trước khi đưa vào PaddleOCR/PP-Structure
- Quét virus (vd. ClamAV) cho file upload trước khi xử lý — nguồn file scan từ bên ngoài mặc định không tin cậy
- Cứng hoá thư viện parse PDF (chống decompression bomb, tắt thực thi JS/script nhúng trong PDF nếu dùng renderer có hỗ trợ)

### 10.5 Audit & giám sát

- Log kỹ thuật (lỗi, thời gian xử lý) **không** chứa nội dung tài liệu — giữ nguyên nguyên tắc đã chốt
- Tách riêng audit trail (ai gọi API, job nào, lúc nào, tenant nào) khỏi log kỹ thuật — phục vụ yêu cầu truy vết sau này của công chứng viên/kiểm toán
- Nếu khách hàng công chứng cần bằng chứng nhật ký không thể sửa, cân nhắc log dạng append-only/hash-chain

### 10.6 Chuỗi cung ứng phần mềm & mô hình AI

- Quét lỗ hổng dependency định kỳ (`pip-audit`, `trivy`), pin version trong lockfile, không dùng tag `latest`
- Xác nhận checksum/nguồn gốc model weight PaddleOCR trước khi triển khai — tránh rủi ro model bị thay/đầu độc (tham chiếu OWASP ML Security Top 10, NIST AI RMF)

### 10.7 Định hướng chứng nhận dài hạn

- ISO/IEC 27001:2022 là đích cần hướng tới khi bán cho Sở ban ngành/trường công (rào cản đã ghi nhận ở Mục 2, xem [business.md](business.md)) — chưa cần cho pilot với công chứng/kế toán
- NIST CSF 2.0 có thể dùng làm khung tự đánh giá nội bộ trước khi đủ quy mô để theo đuổi ISO 27001 chính thức

### 10.8 Ký (sign) payload webhook gửi đi

Mục 10.2.1 đã lo chiều "gọi `callback_url` có an toàn không" (chống SSRF). Còn thiếu chiều ngược lại: bên nhận (web app) làm sao chắc chắn payload nhận được đúng là từ `ocr-engine`, không bị giả mạo/sửa đổi giữa đường.

- Mỗi request webhook kèm header `X-Signature: HMAC-SHA256(body, tenant_secret)` — `tenant_secret` cấp riêng cùng lúc với API key, không dùng chung 1 secret cho ký request đến và ký webhook đi
- Bên nhận verify chữ ký trước khi tin nội dung — giống mô hình Stripe/GitHub webhook
- Kèm timestamp trong payload đã ký để chống replay (bên nhận từ chối nếu timestamp quá cũ, vd > 5 phút)

Chi tiết `tenant_secret` (sinh, lưu trữ, rotation, vì sao chọn HMAC đối xứng): xem Mục 9.4.3 trong [api.md](api.md).
