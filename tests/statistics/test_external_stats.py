from epicsarchiver.statistics._external_stats import (
    _check_internal,
    _check_suffix_match,
)


def test_check_suffix_match() -> None:
    assert _check_suffix_match("as-SR_3_Time") == "as-SR_3_Time"
    assert _check_suffix_match("yPID") == "PID"
    assert _check_suffix_match("B") is None


def test_internal() -> None:
    assert _check_internal("B#B")
    assert _check_internal("#B")
    assert not _check_internal("B")
