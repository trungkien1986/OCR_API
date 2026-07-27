"""Test OCR/nhận diện bảng THẬT trên BCTC PDF thật — chậm (tải model PaddleOCR/
PP-StructureV3 + suy luận CPU), đánh dấu `slow`, KHÔNG chạy trong CI mặc định
(pyproject.toml: `addopts = "-m 'not slow'"`). Gọi thẳng extract_bctc(), không qua
API/queue — phần wiring đó đã được bộ test nhanh (mock_pipeline) bao phủ riêng."""

from pathlib import Path

import pytest

from extractors.bctc import extract_bctc

_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "bctc"

pytestmark = pytest.mark.slow


@pytest.mark.parametrize("pdf_path", sorted(_FIXTURE_DIR.glob("*.pdf")) or [None])
def test_extract_bctc_on_real_pdf(pdf_path: Path | None) -> None:
    if pdf_path is None:
        pytest.skip(f"chưa có fixture BCTC PDF thật trong {_FIXTURE_DIR}")

    result = extract_bctc(str(pdf_path))

    assert result["pages_processed"] > 0
    chi_tieu = result["extracted_data"]["bang_can_doi_ke_toan"]["chi_tieu"]
    assert len(chi_tieu) > 0, "không nhận diện được mã số nào — kiểm tra lại bảng/OCR"

    ma_so_found = {item["ma_so"] for item in chi_tieu}
    # 270 (Tổng cộng tài sản) là mã số hầu như luôn có trên mọi BCTC — nhận diện thiếu
    # đúng mã số này là dấu hiệu pipeline có vấn đề, không phải fixture xấu.
    assert "270" in ma_so_found, f"thiếu mã số 270 (Tổng cộng tài sản), tìm thấy: {ma_so_found}"
