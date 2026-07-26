---
name: monitoring-alerting
description: "Monitoring/alerting production cho ocr-engine — PLG stack tự host, alerting KHÔNG hardcode vào Telegram (máy chưa chắc có internet + Telegram từng bị chặn ở VN), uptime check bắt buộc, backup Postgres ra ngoài máy, pilot là best-effort không hứa SLA"
metadata: 
  node_type: memory
  type: project
  originSessionId: 49bddbc6-5ce5-4f38-9e40-5c12e78ef8ed
  modified: 2026-07-26T03:34:38.572Z
---

Đã thêm Mục 9.5 vào `design/api.md` (trong `OCR_ENGINE_DESIGN.md` đã tách module — xem [[doc-structure]]) — trước đó chưa có thiết kế monitoring/alerting cụ thể, chỉ có Mục 9.3 nhắc chung chung.

**Quyết định chính:**
- **Stack**: Prometheus + Grafana + Loki (PLG, self-host, chạy thêm container trong `docker-compose.yml`) — không cần SaaS đắt tiền, phù hợp 1 máy/2 người/ngân sách nhỏ ([[pricing-value-framework]] cùng tinh thần "không build/mua quá nhu cầu").
- **Alerting 3 mức** (khẩn cấp/cảnh báo/thông tin) qua Alertmanager — **KHÔNG hardcode kênh vào Telegram**. User phản hồi đúng: máy hiện tại nằm trong mạng nội bộ, chưa chắc có internet ổn định (chỉ bản dự định public sau này mới chắc chắn có), và Telegram từng bị chặn/giảm tốc ở một số ISP Việt Nam theo từng giai đoạn — đặt cược alerting vào riêng Telegram là rủi ro thật. Thứ tự ưu tiên kênh theo độ chắc chắn khả dụng: (1) Grafana dashboard qua mạng nội bộ/VPN — luôn khả dụng, không cần internet, vận hành viên tự xem định kỳ nếu không có kênh push nào; (2) SMTP email — ưu tiên hơn 1 app cụ thể vì là giao thức chuẩn phân tán; (3) SMS qua gateway trong nước (eSMS/SpeedSMS) cho cảnh báo khẩn; (4) Telegram/Zalo OA — chỉ là kênh phụ/tiện lợi khi máy đã internet-facing ổn định, Zalo (dịch vụ trong nước) đáng cân nhắc hơn Telegram cho riêng thị trường VN.
- **Uptime check ngoài máy production, điều chỉnh theo chế độ kết nối**: nếu chưa internet-facing, dùng 1 máy KHÁC trong cùng mạng LAN ping health endpoint (không phải dịch vụ public); khi đã internet-facing mới thêm heartbeat public (UptimeRobot...) làm lớp bổ sung. Nguyên tắc xuyên suốt: hệ thống giám sát không được sập chung với máy nó giám sát.
- **Backup Postgres tự động, lưu ra ngoài máy** — vì Postgres là nơi duy nhất giữ audit trail ([[validation-rule-engine]] rules_version, Mục 10.5), máy chỉ có 1 không có redundancy, mất máy = mất audit trail vĩnh viễn nếu không backup.
- **Log rotation Docker** (`max-size`/`max-file`) phải cấu hình từ đầu, tránh đầy đĩa.
- **Không hứa SLA uptime chính thức với khách hàng pilot** — 1 máy không failover, nói rõ đây là best-effort, khớp tinh thần minh bạch đã có ở [[competition-gtm]] (xây niềm tin bằng case study, không phải lời hứa quá mức).

**Why quan trọng phải nhớ:** đây là quyết định firm về công cụ/kiến trúc giám sát, không phải câu hỏi mở cần hỏi lại user.
