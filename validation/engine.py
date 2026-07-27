"""Rule engine cấu hình YAML cho validation_flags — KHÔNG hardcode if/else rải rác
trong extractor (design/pipeline.md Mục 8.6, memory validation_rule_engine). Chỉ hỗ
trợ 2 dạng biểu thức an toàn (regex, không phải eval() trên chuỗi tuỳ ý):

    sum(100,120,130) == 270      # tổng nhiều mã số phải khớp 1 mã số tổng hợp
    270 == 440                    # 2 mã số phải bằng nhau (đối chiếu chéo)

Đây là 2 dạng đủ dùng cho nhóm rule "công thức trong-1-tài-liệu" (Mục 8.6 điểm 2,
nhóm đầu tiên) — mở rộng thêm dạng biểu thức khác (vd đối chiếu số-vs-chữ, đối chiếu
giữa nhiều giấy tờ) là việc của các phase sau, không phải hôm nay."""

import re
from typing import Any, TypedDict

_SUM_EQ_RE = re.compile(r"^\s*sum\(([\d,\s]+)\)\s*==\s*(\d+)\s*$")
_EQ_RE = re.compile(r"^\s*(\d+)\s*==\s*(\d+)\s*$")

# Sai lệch trong ngưỡng làm tròn kế toán không tính là lỗi — tránh false positive vì
# BCTC thật đôi khi lệch 1 đơn vị do làm tròn số liệu gốc.
_TOLERANCE = 1.0


class Rule(TypedDict):
    rule_id: str
    doc_type: str
    fields_involved: list[str]
    expression: str
    severity: str
    message_template: str


class ValidationFlag(TypedDict):
    rule_id: str
    ma_so: str
    issue: str
    severity: str
    expected: float
    actual: float
    delta: float


def _resolve(ma_so_values: dict[str, float], ma_so: str) -> float | None:
    return ma_so_values.get(ma_so)


def evaluate_rules(rules: list[Rule], ma_so_values: dict[str, float]) -> list[ValidationFlag]:
    flags: list[ValidationFlag] = []
    for rule in rules:
        expr = rule["expression"]

        sum_match = _SUM_EQ_RE.match(expr)
        eq_match = _EQ_RE.match(expr) if sum_match is None else None
        if sum_match is not None:
            component_codes = [c.strip() for c in sum_match.group(1).split(",")]
            target_code = sum_match.group(2)
        elif eq_match is not None:
            component_codes = [eq_match.group(1)]
            target_code = eq_match.group(2)
        else:
            continue  # biểu thức không đúng 2 dạng hỗ trợ — bỏ qua, không phải lỗi runtime

        component_values = [_resolve(ma_so_values, c) for c in component_codes]
        target_value = _resolve(ma_so_values, target_code)
        if target_value is None or any(v is None for v in component_values):
            continue  # thiếu mã số (bảng không nhận diện được dòng đó) — không đủ dữ liệu để so

        component_sum = sum(v for v in component_values if v is not None)
        # sum(...) == target: target_code là số đã báo cáo (actual), tổng linh kiện là
        # số tính ra được (expected). code1 == code2 (đối chiếu chéo, không phải tổng):
        # theo đúng thứ tự message_template (vd "270 (actual) != 440 (expected)"), vế
        # trái là actual, vế phải là expected — ngược chiều so với dạng sum(...).
        if sum_match is not None:
            actual, expected = target_value, component_sum
        else:
            actual, expected = component_sum, target_value
        delta = actual - expected
        if abs(delta) > _TOLERANCE:
            flags.append(
                ValidationFlag(
                    rule_id=rule["rule_id"],
                    ma_so=target_code,
                    issue=rule["message_template"].format(expected=expected, actual=actual, delta=delta),
                    severity=rule["severity"],
                    expected=expected,
                    actual=actual,
                    delta=delta,
                )
            )
    return flags


def load_rules(path: str, doc_type: str) -> list[Rule]:
    import yaml

    with open(path, encoding="utf-8") as f:
        raw: list[dict[str, Any]] = yaml.safe_load(f) or []
    return [
        Rule(
            rule_id=r["rule_id"],
            doc_type=r["doc_type"],
            fields_involved=r["fields_involved"],
            expression=r["expression"],
            severity=r["severity"],
            message_template=r["message_template"],
        )
        for r in raw
        if r.get("doc_type") == doc_type
    ]
