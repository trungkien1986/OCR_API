"""Wrapper PaddleOCR — load model 1 lần/worker process (design/pipeline.md Mục 9.2 điểm 6),
KHÔNG load lại trong hàm xử lý từng job. `lang="vi"` chọn đúng dòng model đa ngôn ngữ có hỗ
trợ tiếng Việt của PaddleOCR — KHÔNG phải cấu hình PP-OCRv5 mặc định, vì PP-OCRv5 (bản model
mới nhất) chỉ hỗ trợ 5 ngôn ngữ (Trung giản/phồn thể, pinyin, Anh, Nhật), không có tiếng Việt
(đã sửa lại nhận định sai ở design/architecture.md Mục 6 — xem plans/)."""

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import numpy as np
from paddleocr import PaddleOCR


@dataclass(frozen=True)
class RecognizedLine:
    text: str
    confidence: float
    box: tuple[float, float, float, float]  # (x_min, y_min, x_max, y_max)


@lru_cache(maxsize=1)
def _get_engine() -> PaddleOCR:
    return PaddleOCR(
        lang="vi",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )


def recognize_page(image: np.ndarray) -> list[RecognizedLine]:
    engine = _get_engine()
    lines: list[RecognizedLine] = []
    for result in engine.predict(image):
        data: dict[str, Any] = result.json
        texts = data.get("rec_texts", [])
        scores = data.get("rec_scores", [])
        boxes = data.get("rec_boxes", [])
        for text, score, box in zip(texts, scores, boxes, strict=False):
            lines.append(
                RecognizedLine(
                    text=text,
                    confidence=float(score),
                    box=(float(box[0]), float(box[1]), float(box[2]), float(box[3])),
                )
            )
    return lines
