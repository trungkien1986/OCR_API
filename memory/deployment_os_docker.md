---
name: deployment-os-docker
description: ocr-engine chạy trên Ubuntu Server + Docker Compose, không dùng Windows Service
metadata:
  type: project
---

Quyết định triển khai: máy chạy `ocr-engine` (i5-14500/32GB, CPU-only) dùng **Ubuntu Server** (không GUI), không dùng Windows. Toàn bộ containerize bằng **Docker Compose** (API + worker + Redis), quản lý bằng restart policy (`restart: unless-stopped`), không chạy native process rồi bọc thủ công bằng NSSM/Windows Service. Xem `OCR_ENGINE_DESIGN.md` mục 5.1.

**Why:** Máy này dành riêng cho `ocr-engine`, không dùng chung việc khác — nên không có lý do phải giữ Windows. PaddleOCR/OpenVINO và Redis native/ổn định hơn trên Linux; `systemd` quản lý service trưởng thành hơn Windows Service; tránh overhead ảo hoá của Docker Desktop trên Windows (WSL2/Hyper-V) vốn đáng kể với workload CPU-only đã tính sát nhu cầu. Người dùng đã đồng ý đề xuất này sau khi được phân tích trade-off.

**How to apply:**
- Môi trường chính thức để code/test/triển khai: Ubuntu Server + Docker Compose — không thiết kế theo hướng Windows Service.
- Khả năng chạy trên Windows (demo/máy dự phòng) vẫn giữ gần miễn phí nhờ containerize — không cần bộ triển khai native riêng cho Windows.
- Giữ kỷ luật code cross-platform để không phá vỡ khả năng đó: dùng `pathlib` thay vì hardcode dấu `/`, không gọi lệnh shell đặc thù OS, không hardcode đường dẫn kiểu `/tmp/...`.
- Liên quan tới [[grpc-protobuf-readiness]] — cả hai đều là nguyên tắc thiết kế hạ tầng/kênh giao tiếp cần giữ xuyên suốt khi code.
