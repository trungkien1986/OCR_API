"""Parser số kiểu Việt Nam cho BCTC (design/pipeline.md Mục 8.2): dấu CHẤM phân cách
nghìn, dấu PHẨY phân cách thập phân (ngược quy ước Anh-Mỹ), số âm viết trong ngoặc đơn
`(x)`. KHÔNG dùng parser mặc định kiểu Anh-Mỹ (float()/locale mặc định) — sẽ đọc sai
hoàn toàn ("1.234.567" kiểu Anh-Mỹ = 1.234567, không phải 1234567)."""

import re

# Ô trống/không có số liệu trong BCTC thường ghi bằng dấu gạch ngang đơn lẻ (hoặc rỗng)
# — không phải giá trị 0, mà là "không áp dụng/không có phát sinh". Trả về None để phân
# biệt rõ với 0 thật, tránh rule engine hiểu nhầm mọi ô trống là 0 rồi báo lệch sai.
_BLANK_RE = re.compile(r"^[-–—\s]*$")
_NUMBER_RE = re.compile(r"^\(?-?[\d.,\s]+\)?$")


def parse_vn_number(raw: str) -> float | None:
    text = raw.strip()
    if _BLANK_RE.match(text):
        return None
    if not _NUMBER_RE.match(text):
        return None

    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1].strip()
    text = text.replace(" ", "")
    if text.startswith("-"):
        negative = True
        text = text[1:]

    if not text:
        return None

    # Phẩy cuối cùng (nếu có) là dấu thập phân; mọi dấu chấm là phân cách nghìn.
    if "," in text:
        integer_part, _, fraction_part = text.rpartition(",")
        integer_part = integer_part.replace(".", "")
    else:
        integer_part, fraction_part = text.replace(".", ""), ""

    if not integer_part or not integer_part.isdigit():
        return None
    if fraction_part and not fraction_part.isdigit():
        return None

    value = float(f"{integer_part}.{fraction_part}") if fraction_part else float(integer_part)
    return -value if negative else value
