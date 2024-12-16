from typing import Sequence

import epicsarchiver.retrieval.EPICSEvent_pb2 as ee
from epicsarchiver.retrieval.EPICSEvent_pb2 import ScalarInt
from epicsarchiver.retrieval.pb import EeEvent, escape_bytes


def create_pb_bytes(
    events: Sequence[EeEvent],
    info: ee.PayloadInfo,
) -> bytes:
    """Converts list of events to escaped protobuf bytes.

    Args:
        events (list[EeEvent]): list of events
        info (ee.PayloadInfo): payload data

    Returns:
        bytes: escaped bytes
    """
    info_bytes = escape_bytes(info.SerializeToString())
    events_bytes = b"\n".join(escape_bytes(e.SerializeToString()) for e in events)
    return info_bytes + b"\n" + events_bytes


TEST_EVENTS = [
    ScalarInt(
        secondsintoyear=22537583,
        val=1,
        nano=931598267,
        severity=0,
        status=0,
        fieldvalues=[ee.FieldValue(name="hey", val="ho")],
    ),
    ScalarInt(
        secondsintoyear=22537584,
        val=2,
        nano=907631989,
        severity=0,
        status=0,
        fieldvalues=[ee.FieldValue(name="hey", val="ho")],
    ),
    ScalarInt(
        secondsintoyear=22537585,
        val=3,
        nano=931598267,
        severity=0,
        status=0,
        fieldvalues=[ee.FieldValue(name="hey", val="ho")],
    ),
    ScalarInt(
        secondsintoyear=22537586,
        val=4,
        nano=911606448,
        severity=0,
        status=0,
        fieldvalues=[ee.FieldValue(name="hey", val="ho")],
    ),
]
