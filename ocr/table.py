"""Wrapper PP-StructureV3 — nhận diện bảng (design/pipeline.md Mục 8.2), load model 1
lần/worker process, cùng nguyên tắc với ocr/engine.py.

CHÚ Ý: PP-StructureV3 luôn tái dựng bảng nhận diện được dưới dạng HTML (`<table>...`),
kể cả bảng không viền (wireless) — đây là định dạng output ổn định qua các bản PaddleOCR,
nên dùng thay vì đọc thẳng cấu trúc JSON nội bộ (tên field dễ đổi giữa các version, chưa
có tài liệu chính thức mô tả đầy đủ tại thời điểm viết). `_find_table_html()` dò tìm theo
tên field phổ biến thay vì giả định 1 đường dẫn cố định — cần XÁC MINH LẠI khi chạy thật
lần đầu qua Docker (bước kiểm chứng cuối kế hoạch), vì đây là phần rủi ro nhất về API."""

from functools import lru_cache
from typing import Any

import numpy as np
from paddleocr import PPStructureV3

_TABLE_HTML_KEYS = ("html", "pred_html", "table_html")


@lru_cache(maxsize=1)
def _get_engine() -> PPStructureV3:
    return PPStructureV3()


def detect_tables_html(image: np.ndarray) -> list[str]:
    engine = _get_engine()
    tables: list[str] = []
    for result in engine.predict(image):
        tables.extend(_find_table_html(result.json))
    return tables


def _find_table_html(node: Any) -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        for key in _TABLE_HTML_KEYS:
            value = node.get(key)
            if isinstance(value, str) and "<table" in value.lower():
                found.append(value)
        for value in node.values():
            found.extend(_find_table_html(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_find_table_html(item))
    return found
