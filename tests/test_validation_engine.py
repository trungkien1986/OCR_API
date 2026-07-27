from validation.engine import Rule, evaluate_rules


def _rule(**overrides: object) -> Rule:
    base: Rule = {
        "rule_id": "test_sum",
        "doc_type": "bctc",
        "fields_involved": ["110", "120", "100"],
        "expression": "sum(110,120) == 100",
        "severity": "error",
        "message_template": "100 ({actual}) != 110+120 ({expected})",
    }
    base.update(overrides)  # type: ignore[typeddict-item]
    return base


def test_sum_rule_passes_when_balanced() -> None:
    flags = evaluate_rules([_rule()], {"110": 100.0, "120": 200.0, "100": 300.0})
    assert flags == []


def test_sum_rule_flags_when_unbalanced() -> None:
    flags = evaluate_rules([_rule()], {"110": 100.0, "120": 200.0, "100": 999.0})
    assert len(flags) == 1
    flag = flags[0]
    assert flag["rule_id"] == "test_sum"
    assert flag["ma_so"] == "100"
    assert flag["severity"] == "error"
    assert flag["expected"] == 300.0
    assert flag["actual"] == 999.0
    assert flag["delta"] == 699.0


def test_rule_skipped_when_field_missing() -> None:
    flags = evaluate_rules([_rule()], {"110": 100.0})
    assert flags == []


def test_direct_equality_rule() -> None:
    rule = _rule(
        rule_id="test_eq",
        fields_involved=["270", "440"],
        expression="270 == 440",
        message_template="270 ({actual}) != 440 ({expected})",
    )
    assert evaluate_rules([rule], {"270": 100.0, "440": 100.0}) == []
    flags = evaluate_rules([rule], {"270": 100.0, "440": 90.0})
    assert len(flags) == 1
    assert flags[0]["delta"] == 10.0


def test_tolerance_absorbs_rounding_noise() -> None:
    flags = evaluate_rules([_rule()], {"110": 100.0, "120": 200.0, "100": 300.4})
    assert flags == []
