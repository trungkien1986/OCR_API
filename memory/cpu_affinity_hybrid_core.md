---
name: cpu-affinity-hybrid-core
description: "Không tự pin worker process vào core theo index cứng — i5-14500 là CPU hybrid P-core/E-core, dùng cgroup quota thay vì taskset/affinity mask"
metadata: 
  node_type: memory
  type: project
  originSessionId: 49bddbc6-5ce5-4f38-9e40-5c12e78ef8ed
  modified: 2026-07-26T02:20:26.441Z
---

Quyết định kiến trúc cho `ocr-engine`: **không tự ghim (pin) worker process vào core CPU theo index cứng** (`taskset -c`, `SetProcessAffinityMask`, `os.sched_setaffinity` với danh sách ID cụ thể) ở bất kỳ tầng nào của code. Thay vào đó giới hạn CPU bằng **cgroup quota** (đã áp dụng qua `deploy.resources.limits.cpus` trong `docker-compose.yml`) và để scheduler của Linux (CFS) tự chọn core. Xem `OCR_ENGINE_DESIGN.md` Mục 9.2, điểm 1-2.

**Why:** Người dùng từng gặp lỗi thực tế ở dự án khác (Windows) khi code tự ghim process vào core theo index. Nguyên nhân gốc: CPU của máy `ocr-engine` (i5-14500) là kiến trúc **hybrid** — 6 P-core × 2 luồng (SMT) + 8 E-core × 1 luồng = 20 luồng, không đồng đều. Code giả định "mọi core như nhau" (uniform core) rồi ghim theo index cứng sẽ gán nhầm luồng nặng vào E-core yếu hoặc core đang bận — đây là **lỗi giả định của code, không phải lỗi hệ điều hành**, nên xảy ra được trên cả Windows lẫn Linux nếu code tự ghim core. Windows Server không tự động "miễn nhiễm" lỗi này — chỉ là ít bị test trên tổ hợp CPU hybrid desktop + Server OS trong thực tế nên ít ai báo lỗi, không phải vì kernel Server xử lý hybrid-core tốt hơn về bản chất.

**How to apply:**
- Không dùng `taskset`/`SetProcessAffinityMask`/`sched_setaffinity` với ID core cụ thể trong code hay script triển khai.
- Giới hạn CPU của container/process bằng cgroup quota (số lượng CPU-time, không phải danh sách core ID) — Linux CFS tự chọn core phù hợp, kể cả nhân 5.18+/6.x đã hybrid-aware.
- Số worker process (RQ) tune bằng benchmark thực tế (bắt đầu 4-6, tăng dần tới điểm bão hoà throughput), không suy diễn từ số luồng lý thuyết (20) — vì P-core và E-core không đóng góp compute ngang nhau.
- Nếu tương lai thật sự cần pin core (hiếm khi cần), phải xác nhận topology thật bằng `lscpu -e` (cột core-type phân biệt P/E) trước, không giả định core index tuần tự đồng nhất.
- Liên quan [[deployment_os_docker]] — cùng nằm trong nhóm quyết định hạ tầng/triển khai của dự án này.
