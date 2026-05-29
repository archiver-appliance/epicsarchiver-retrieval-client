"""Fake archiver data for documentation notebooks."""

import math

import epicsarchiver.retrieval.EPICSEvent_pb2 as ee
from epicsarchiver.retrieval.EPICSEvent_pb2 import (
    SCALAR_DOUBLE,
    PayloadInfo,
    ScalarDouble,
)
from epicsarchiver.retrieval.pb import escape_bytes

_YEAR = 2026
_BASE_SECS = 8_640_000  # 2026-04-21 00:00:00 UTC (seconds into year)


def make_doc_events(n: int = 30) -> list[ScalarDouble]:
    return [
        ScalarDouble(
            secondsintoyear=_BASE_SECS + i * 10,
            nano=int(abs(math.sin(i)) * 1_000_000_000),
            val=28.0 + 0.5 * math.sin(i * 0.4),
            severity=1,
            status=4,
            fieldvalues=[
                ee.FieldValue(name="EGU", val="degC"),
                ee.FieldValue(name="PREC", val="2"),
            ],
        )
        for i in range(n)
    ]


def create_pb_bytes(pvname: str, year: int = _YEAR) -> bytes:
    events = make_doc_events()
    info = PayloadInfo(type=SCALAR_DOUBLE, pvname=pvname, year=year)
    info_bytes = escape_bytes(info.SerializeToString())
    events_bytes = b"\n".join(escape_bytes(e.SerializeToString()) for e in events)
    return info_bytes + b"\n" + events_bytes
