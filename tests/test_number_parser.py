import pytest

from extractors.number_parser import parse_vn_number


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1.234.567", 1234567.0),
        ("1.234.567,89", 1234567.89),
        ("0", 0.0),
        ("100", 100.0),
        ("(500.000)", -500000.0),
        ("-500.000", -500000.0),
        ("-", None),
        ("", None),
        ("  -  ", None),
        ("1,5", 1.5),
        ("abc", None),
    ],
)
def test_parse_vn_number(raw: str, expected: float | None) -> None:
    assert parse_vn_number(raw) == expected
