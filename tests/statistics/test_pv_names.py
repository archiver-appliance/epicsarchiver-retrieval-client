from epicsarchiver.statistics.pv_names import (
    _check_internal,
    _check_suffix_match,
    _get_pv_parts,
    _get_pv_parts_stats,
)


def test_get_pv_parts() -> None:
    assert _get_pv_parts("DTL-030:EMR-SM-003:Axis.URIP") == ["DTL-030", "EMR-SM"]


def test_get_pv_parts_stats() -> None:
    assert _get_pv_parts_stats({
        "DTL-030:EMR-SM-003:Axis.URIP",
        "DTL-030:EMR-SG-003:Axis.URIQ",
        "DTL-030:EMR-SG-002:Axis.URIQ",
    }) == {
        "device": [("EMR-SM", 1), ("EMR-SG", 2)],
        "system": [("DTL-030", 3)],
    }


def test_check_suffix_match() -> None:
    assert _check_suffix_match("as-SR_3_Time") == "as-SR_3_Time"
    assert _check_suffix_match("yPID") == "PID"
    assert _check_suffix_match("B") is None


def test_internal() -> None:
    assert _check_internal("B#B")
    assert _check_internal("#B")
    assert not _check_internal("B")
