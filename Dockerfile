FROM python:3.11-slim

# Thư viện hệ thống PaddleOCR/OpenCV cần (xử lý ảnh, không phải OCR model)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bake model PaddleOCR/PP-StructureV3 vào image ngay lúc build — máy production chưa
# chắc có internet ổn định (design/api.md Mục 9.5), KHÔNG được để tải lazy lúc chạy job
# đầu tiên. Đặt trước COPY . . để tận dụng cache layer (không tải lại khi chỉ sửa code).
RUN python -c "\
from paddleocr import PaddleOCR, PPStructureV3; \
PaddleOCR(lang='vi', use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False); \
PPStructureV3()"

COPY . .

RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
