---
name: grpc-protobuf-readiness
description: ocr-engine phải thiết kế để dễ nâng cấp sang gRPC/Protobuf sau này, dù hiện tại dùng JSON/REST
metadata:
  type: project
---

Quyết định kiến trúc: `ocr-engine` dùng JSON/REST làm API chính ở giai đoạn pilot (xem `OCR_ENGINE_DESIGN.md` mục 9.1), nhưng phải luôn thiết kế sao cho **sẵn sàng nâng cấp lên gRPC/Protobuf** khi cần, không phải viết lại từ đầu.

**Why:** Người dùng chủ động xác nhận thích hướng gRPC/Protobuf (hiệu năng/băng thông tốt hơn JSON cho giao tiếp nội bộ tần suất cao) sau khi được giải thích khái niệm, và muốn đây là một ràng buộc thiết kế xuyên suốt dự án, không chỉ là lựa chọn tương lai tuỳ nghi.

**How to apply:**
- Khi thiết kế response schema (JSON Schema versioned, mục 9.1 của `OCR_ENGINE_DESIGN.md`), giữ cấu trúc dữ liệu ổn định, phẳng, có kiểu rõ ràng — tránh field quá tự do/động (dynamic dict lồng sâu) để sau này ánh xạ sang Protobuf message dễ dàng.
- Tách rõ domain model (Pydantic) khỏi lớp serialize HTTP/JSON, để khi thêm gRPC service song song thì logic nghiệp vụ không phải viết lại.
- Khi đặt tên/thứ tự field trong schema, cân nhắc luôn tính nhất quán với quy ước Protobuf (tên field không đổi ý nghĩa qua các version) để việc viết `.proto` sau này chỉ là ánh xạ 1-1.
- Việc này áp dụng cho kênh nội bộ (worker ↔ web app) trước tiên — API công khai hướng ngoài vẫn giữ JSON/REST vì dễ tích hợp cho khách hàng bên ngoài.
- Liên quan tới [[deployment_os_docker]] — cả hai đều là nguyên tắc thiết kế hạ tầng/kênh giao tiếp cần giữ xuyên suốt khi code.
