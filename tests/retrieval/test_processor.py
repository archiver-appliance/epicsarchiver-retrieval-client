from epicsarchiver.retrieval.archiver_retrieval.processor import (
    Processor,
    ProcessorName,
)


def test_calc_pv_name() -> None:
    pv = "PVNAME"
    expected_result = "firstSample_60(PVNAME)"
    assert Processor(ProcessorName.FIRSTSAMPLE, 60).calc_pv_name(pv) == expected_result
