"""Extractor cho doc_type=bctc — ghép tiền xử lý + OCR + nhận diện bảng + map mã số
Thông tư 200 (Mẫu B01-DN, Bảng cân đối kế toán) + rule engine validate (design/pipeline.md
Mục 8, 8.2, 8.6). Giới hạn v1 đã ghi rõ ở pipeline.md: chỉ hỗ trợ bảng header 1 dòng —
bảng phụ lục/thuyết minh phức tạp hơn rơi vào review_required=true thay vì cố map sai."""

import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz, process

from extractors.ma_so_200 import MA_SO_200
from extractors.number_parser import parse_vn_number
from ocr import engine as ocr_engine
from ocr import preprocess
from ocr import table as ocr_table
from validation.engine import ValidationFlag, evaluate_rules, load_rules

_MA_SO_RE = re.compile(r"^\d{3}$")
_RULES_PATH = str(Path(__file__).parent.parent / "validation" / "rules_bctc.yaml")
# Ngưỡng fuzzy-match tên chỉ tiêu — dưới ngưỡng này coi như không đủ tin cậy để gán mã số
# theo tên, thà bỏ qua dòng đó còn hơn map sai (design/pipeline.md: "review_required thay
# vì cố map sai").
_NAME_MATCH_CUTOFF = 70.0


class _TableRowParser(HTMLParser):
    """Trích rows/cells từ HTML bảng PP-StructureV3 trả về — chỉ cần text từng ô,
    không cần giữ style/thuộc tính."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._current_row: list[str] | None = None
        self._current_cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._current_row = []
        elif tag in ("td", "th"):
            self._current_cell = []

    def handle_data(self, data: str) -> None:
        if self._current_cell is not None:
            self._current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self._current_cell is not None:
            text = "".join(self._current_cell).strip()
            if self._current_row is not None:
                self._current_row.append(text)
            self._current_cell = None
        elif tag == "tr" and self._current_row is not None:
            self.rows.append(self._current_row)
            self._current_row = None


def _parse_html_rows(html: str) -> list[list[str]]:
    parser = _TableRowParser()
    parser.feed(html)
    return parser.rows


def _match_ma_so(cells: list[str]) -> str | None:
    for cell in cells:
        candidate = cell.strip()
        if _MA_SO_RE.match(candidate) and candidate in MA_SO_200:
            return candidate

    name_cell = max((c for c in cells if parse_vn_number(c) is None), key=len, default="")
    if not name_cell:
        return None
    match = process.extractOne(
        name_cell, MA_SO_200, scorer=fuzz.token_sort_ratio, score_cutoff=_NAME_MATCH_CUTOFF
    )
    return None if match is None else match[2]


def _extract_numbers(cells: list[str]) -> list[float]:
    return [v for c in cells if (v := parse_vn_number(c)) is not None]


def extract_bctc(file_path: str) -> dict[str, Any]:
    has_text_layer = preprocess.has_text_layer(file_path)
    images = preprocess.rasterize_pdf(file_path)
    if not has_text_layer:
        images = [preprocess.deskew(img) for img in images]

    if has_text_layer:
        # PDF xuất từ máy tính — text layer gần như chính xác tuyệt đối (Mục 8.1),
        # không cần OCR để lấy confidence; PP-StructureV3 vẫn cần ẢNH để nhận diện
        # cấu trúc bảng (hàng/cột không nằm trong text layer thô).
        confidence_overall: float | None = 1.0
    else:
        scores = [line.confidence for image in images for line in ocr_engine.recognize_page(image)]
        confidence_overall = sum(scores) / len(scores) if scores else None

    ma_so_values: dict[str, float] = {}
    chi_tieu: list[dict[str, Any]] = []
    tables_found = 0
    for image in images:
        for table_html in ocr_table.detect_tables_html(image):
            tables_found += 1
            for row in _parse_html_rows(table_html):
                ma_so = _match_ma_so(row)
                if ma_so is None:
                    continue
                numbers = _extract_numbers(row)
                if not numbers:
                    continue
                so_cuoi_ky = numbers[0]
                so_dau_ky = numbers[1] if len(numbers) > 1 else None
                ma_so_values[ma_so] = so_cuoi_ky
                chi_tieu.append(
                    {
                        "ma_so": ma_so,
                        "ten_chi_tieu": MA_SO_200[ma_so],
                        "so_cuoi_ky": so_cuoi_ky,
                        "so_dau_ky": so_dau_ky,
                    }
                )

    rules = load_rules(_RULES_PATH, doc_type="bctc")
    validation_flags: list[ValidationFlag] = evaluate_rules(rules, ma_so_values)

    # review_required (Mục 8.6 điểm 4): có rule error, HOẶC không nhận diện được bảng nào
    # (giới hạn đã biết). CHƯA áp dụng "confidence dưới ngưỡng đã hiệu chỉnh" — ngưỡng đó
    # cần golden dataset/reliability diagram (Mục 14.2), chưa có ở bước này.
    review_required = tables_found == 0 or any(f["severity"] == "error" for f in validation_flags)

    return {
        "pages_processed": len(images),
        "confidence_overall": confidence_overall,
        "extracted_data": {"bang_can_doi_ke_toan": {"chi_tieu": chi_tieu}},
        "validation_flags": validation_flags,
        "review_required": review_required,
    }
