---
name: cicd-pipeline
description: "CI/CD cho ocr-engine — GitHub private repo + Actions, self-hosted runner ngay trên máy production, cổng duyệt thủ công trước deploy, không cần blue-green"
metadata: 
  node_type: memory
  type: project
  originSessionId: 49bddbc6-5ce5-4f38-9e40-5c12e78ef8ed
  modified: 2026-07-26T03:22:38.354Z
---

Đã thêm Mục 5.2 vào `design/architecture.md` (trong `OCR_ENGINE_DESIGN.md` đã tách module — xem [[doc-structure]]) — thiết kế CI/CD, trước đó chưa có mục nào.

**Quyết định chính:**
- **Git hosting**: GitHub, repo **private**, tách biệt hoàn toàn khỏi công việc ngân hàng ([[deployment-os-docker]] cùng nhóm quyết định hạ tầng).
- **CI mỗi push/PR**: lint (`ruff`) + type check (`mypy`) + unit test + validate JSON Schema + build/scan Docker image (Trivy) + sinh SBOM + push GitHub Container Registry (tag theo git SHA).
- **Regression gate golden dataset TÁCH KHỎI CI nhanh** — chạy OCR thật tốn thời gian trên máy CPU-only, chỉ chạy khi merge `main` hoặc nightly, không chặn mỗi commit.
- **CD dùng self-hosted GitHub Actions runner cài ngay trên máy `ocr-engine`** (không phải runner cloud + SSH) — vì production chỉ có 1 máy cố định, không phải hạ tầng co giãn.
- **Có cổng duyệt thủ công (GitHub Environments + required reviewer) trước khi deploy thật** — vì xử lý dữ liệu cá nhân/tài chính nhạy cảm của khách hàng pilot thật, chưa nên auto-deploy hoàn toàn tự động ở giai đoạn pilot.
- **Không cần zero-downtime/blue-green** — kiến trúc đã async qua Redis Queue, job chờ trong queue an toàn qua vài giây restart container; đầu tư blue-green ở quy mô pilot 2-3 khách hàng là over-engineering.
- **`.env` trên máy production không nằm trong git, không bị CD ghi đè mỗi lần deploy** — chỉ code/image thay đổi, secrets vận hành sống độc lập trên máy. Secrets CI (đăng nhập registry) tách biệt hoàn toàn khỏi secrets nghiệp vụ (`tenant_secret`/`api_key` — dữ liệu runtime trong Postgres).

**Why quan trọng phải nhớ:** đây là quyết định firm (giống cách chốt DB/Thông tư trước đó), không phải câu hỏi mở — không cần hỏi lại user trừ khi họ muốn đổi hướng.
