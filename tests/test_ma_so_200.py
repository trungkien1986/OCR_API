from extractors.ma_so_200 import MA_SO_200, SUBTOTAL_COMPONENTS


def test_key_totals_present() -> None:
    assert MA_SO_200["100"] == "Tài sản ngắn hạn"
    assert MA_SO_200["200"] == "Tài sản dài hạn"
    assert MA_SO_200["270"] == "Tổng cộng tài sản"
    assert MA_SO_200["300"] == "Nợ phải trả"
    assert MA_SO_200["400"] == "Vốn chủ sở hữu"
    assert MA_SO_200["440"] == "Tổng cộng nguồn vốn"


def test_subtotal_components_reference_known_ma_so() -> None:
    for target, components in SUBTOTAL_COMPONENTS.items():
        assert target in MA_SO_200, f"mã số tổng hợp {target} không có trong MA_SO_200"
        for code in components:
            assert code in MA_SO_200, f"thành phần {code} của {target} không có trong MA_SO_200"


def test_ma_so_are_unique_and_numeric() -> None:
    for code in MA_SO_200:
        assert code.isdigit()
