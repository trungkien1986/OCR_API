"""Tiền xử lý PDF trước OCR (design/pipeline.md Mục 8.1):
- Phát hiện PDF đã có text layer sẵn (PDF xuất từ máy tính) — trích trực tiếp,
  KHÔNG chạy OCR (nhanh hơn, chính xác gần như tuyệt đối).
- Chỉ OCR khi không có text layer hoặc text layer rỗng/lỗi (PDF từ máy scan/ảnh chụp).
- Deskew + downsample DPI trước khi đưa qua OCR (Mục 9.2 điểm 8) — scan gốc thường
  300-600 DPI, OCR không cần vượt quá ~200-300 DPI.
"""

import cv2
import numpy as np
import pymupdf

# Ngưỡng số ký tự tối thiểu/trang để coi là "có text layer dùng được" — PDF scan đôi khi
# vẫn có vài ký tự rác (watermark, số trang chèn sẵn) dù ảnh chính là scan thuần.
_MIN_CHARS_PER_PAGE = 20

# OCR không cần vượt quá ~200-300 DPI (Mục 9.2 điểm 8) — scan gốc thường 300-600 DPI.
DEFAULT_OCR_DPI = 200


def has_text_layer(pdf_path: str) -> bool:
    with pymupdf.open(pdf_path) as doc:
        if doc.page_count == 0:
            return False
        avg_chars = sum(len(page.get_text()) for page in doc) / doc.page_count
    return avg_chars >= _MIN_CHARS_PER_PAGE


def extract_text_layer(pdf_path: str) -> list[str]:
    """Trả về text từng trang, dùng khi has_text_layer() đã xác nhận PDF có text layer sẵn."""
    with pymupdf.open(pdf_path) as doc:
        return [page.get_text() for page in doc]


def rasterize_pdf(pdf_path: str, dpi: int = DEFAULT_OCR_DPI) -> list[np.ndarray]:
    """Render mỗi trang PDF thành ảnh (BGR, dùng cho OpenCV/PaddleOCR) ở DPI đã hạ —
    dùng khi PDF không có text layer (scan thuần) hoặc input là ảnh chụp/scan."""
    zoom = dpi / 72  # PyMuPDF mặc định render ở 72 DPI
    matrix = pymupdf.Matrix(zoom, zoom)
    pages: list[np.ndarray] = []
    with pymupdf.open(pdf_path) as doc:
        for page in doc:
            pixmap = page.get_pixmap(matrix=matrix, colorspace=pymupdf.csRGB)
            image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
                pixmap.height, pixmap.width, pixmap.n
            )
            pages.append(cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    return pages


def deskew(image: np.ndarray) -> np.ndarray:
    """Chỉnh nghiêng — hồ sơ công chứng/tín dụng thường scan/chụp nghiêng (Mục 8.1),
    đây là bước tiền xử lý bắt buộc trước OCR, không phải tuỳ chọn."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    threshold = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

    coords = cv2.findNonZero(threshold)
    if coords is None:
        return image  # trang trắng/không có nội dung — không có gì để chỉnh nghiêng
    angle = cv2.minAreaRect(coords)[-1]
    # cv2.minAreaRect trả góc trong [-90, 0) — chuẩn hoá về độ lệch thực tế cần xoay lại.
    angle = -(90 + angle) if angle < -45 else -angle
    if abs(angle) < 0.1:
        return image  # lệch không đáng kể — xoay sẽ chỉ thêm nhiễu nội suy vô ích

    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        image, rotation_matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )
