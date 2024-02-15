from datetime import datetime
from unittest import mock

import numpy as np
from pytz import utc as UTC  # noqa: N812

from epicsarchiver import ArchiveEvent, pb
from epicsarchiver import EPICSEvent_pb2 as ee

TIMESTAMP_2001 = 978307200
TIMESTAMP_INACCURACY = 1e-6


PV = "SR-DI-DCCT-01:SIGNAL"
# The raw bytes containing some Archiver Appliance data.
RAW_PAYLOAD_INFO = (
    b"\x08\x06\x12\x14\x53\x52\x2d\x44\x49\x2d\x44\x43\x43\x54\x2d\x30\x31\x3a\x53"
    b"\x49\x47\x4e\x41\x4c\x18\xdf\x0f\x20\x01"
)
RAW_EVENT = (
    b"\x08\x8f\xd9\xa3\x01\x10\x86\x8f\xfd\x01\x19\x0c\x19\x52\xcb\x7d\x8a\x70\x40"
)
# The contents of a PB file with a header and one event.
PB_CHUNK = RAW_PAYLOAD_INFO + b"\n" + RAW_EVENT
# The actual contents of the above raw strings (PV name is not stored)
EVENT = ArchiveEvent(
    PV,
    264.6557114798495,
    2681999,
    2015,
    4147078,
    0,
    0,
    [],
)


def _pb_event(
    event: ArchiveEvent,
) -> (
    ee.ScalarString
    | ee.ScalarDouble
    | ee.ScalarInt
    | ee.ScalarByte
    | ee.VectorString
    | ee.VectorFloat
    | ee.VectorInt
    | ee.V4GenericBytes
):
    """Create a ProtoBuf event, mostly used for testing.

    Args:
            event (ArchiveEvent): An Archive Event to convert

    Returns:
        ee.ScalarString
    | ee.ScalarDouble
    | ee.ScalarInt
    | ee.ScalarByte
    | ee.VectorString
    | ee.VectorFloat
    | ee.VectorInt
    | ee.V4GenericBytes: An Archive Event in proto buf format
    """
    if isinstance(event.val, int):
        return ee.ScalarInt(
            secondsintoyear=event.secondsintoyear,
            nano=event.nanos,
            val=event.val,
            severity=event.severity,
            status=event.status,
            fieldvalues=None
            if event.field_values is None
            else [ee.FieldValue(name=f.name, val=f.value) for f in event.field_values],
        )
    if isinstance(event.val, float):
        return ee.ScalarDouble(
            secondsintoyear=event.secondsintoyear,
            nano=event.nanos,
            val=event.val,
            severity=event.severity,
            status=event.status,
            fieldvalues=None
            if event.field_values is None
            else [ee.FieldValue(name=f.name, val=f.value) for f in event.field_values],
        )
    if isinstance(event.val, str):
        return ee.ScalarString(
            secondsintoyear=event.secondsintoyear,
            nano=event.nanos,
            val=event.val,
            severity=event.severity,
            status=event.status,
            fieldvalues=None
            if event.field_values is None
            else [ee.FieldValue(name=f.name, val=f.value) for f in event.field_values],
        )
    if isinstance(event.val, bytes):
        return ee.V4GenericBytes(
            secondsintoyear=event.secondsintoyear,
            nano=event.nanos,
            val=event.val,
            severity=event.severity,
            status=event.status,
            fieldvalues=None
            if event.field_values is None
            else [ee.FieldValue(name=f.name, val=f.value) for f in event.field_values],
        )
    if all(isinstance(x, str) for x in event.val):
        return ee.VectorString(
            secondsintoyear=event.secondsintoyear,
            nano=event.nanos,
            val=event.val,  # type: ignore
            severity=event.severity,
            status=event.status,
            fieldvalues=None
            if event.field_values is None
            else [ee.FieldValue(name=f.name, val=f.value) for f in event.field_values],
        )
    if all(isinstance(x, int) for x in event.val):
        return ee.VectorInt(
            secondsintoyear=event.secondsintoyear,
            nano=event.nanos,
            val=event.val,  # type: ignore
            severity=event.severity,
            status=event.status,
            fieldvalues=None
            if event.field_values is None
            else [ee.FieldValue(name=f.name, val=f.value) for f in event.field_values],
        )
    if all(isinstance(x, float) for x in event.val):
        return ee.VectorFloat(
            secondsintoyear=event.secondsintoyear,
            nano=event.nanos,
            val=event.val,  # type: ignore
            severity=event.severity,
            status=event.status,
            fieldvalues=None
            if event.field_values is None
            else [ee.FieldValue(name=f.name, val=f.value) for f in event.field_values],
        )
    return ee.VectorString(
        secondsintoyear=event.secondsintoyear,
        nano=event.nanos,
        val=None,
        severity=event.severity,
        status=event.status,
        fieldvalues=None
        if event.field_values is None
        else [ee.FieldValue(name=f.name, val=f.value) for f in event.field_values],
    )


def test_parse_payloadinfo() -> None:
    pi = ee.PayloadInfo()
    pi.ParseFromString(RAW_PAYLOAD_INFO)
    assert pi.year == 2015
    assert pi.type == 6
    assert pi.pvname == PV


def test_parse_scalardouble() -> None:
    e = ee.ScalarDouble()
    e.ParseFromString(RAW_EVENT)
    if isinstance(EVENT.val, float):
        assert abs(e.val - EVENT.val) < 1e-7
    else:
        raise TypeError
    assert EVENT.secondsintoyear == e.secondsintoyear
    assert EVENT.nanos == e.nano
    assert e.severity == EVENT.severity


def test_parse_pb_data() -> None:
    result = pb.parse_pb_data(PB_CHUNK)
    event = result[0]
    assert event == EVENT


def test_unescape_line_does_not_change_regular_bytes() -> None:
    test_bytes = b"hello:-1|bye"
    assert pb.unescape_bytes(test_bytes) == test_bytes


def test_unescape_bytes_handles_example_escaped_bytes() -> None:
    test_bytes = b"hello" + pb.ESC_BYTE + b"\x02" + b"bye"
    assert pb.unescape_bytes(test_bytes) == b"hello" + pb.NL_BYTE + b"bye"


def test_escape_bytes_does_not_change_regular_bytes() -> None:
    test_bytes = b"hello:-1|bye"
    assert pb.escape_bytes(test_bytes) == test_bytes


def test_escape_bytes_handles_example_unescaped_bytes() -> None:
    test_bytes = b"hello\x0abye\x1b"
    expected = b"hello" + pb.ESC_BYTE + b"\x02" + b"bye" + pb.ESC_BYTE + b"\x01"
    assert pb.escape_bytes(test_bytes) == expected


def test_unescape_bytes_works_in_correct_order_and_is_reversible() -> None:
    test_bytes = b"hello \x1b\x01\x02 bye \x1b\x01\x03"
    expected = b"hello \x1b\x02 bye \x1b\x03"
    unescaped = pb.unescape_bytes(test_bytes)
    assert unescaped == expected
    escaped = pb.escape_bytes(unescaped)
    assert escaped == test_bytes


def test_event_timestamp_gives_correct_answer_1970() -> None:
    event = mock.MagicMock()
    event.secondsintoyear = 10
    event.nano = int(1e7)
    assert pb.event_timestamp(1970, event) == datetime.fromtimestamp(10.01, tz=UTC)


def test_event_timestamp_gives_correct_answer_2001() -> None:
    seconds = 1000
    nanos = 12345
    expected = TIMESTAMP_2001 + seconds + 1e-9 * nanos
    event = mock.MagicMock()
    event.secondsintoyear = seconds
    event.nano = nanos
    assert pb.event_timestamp(2001, event) == datetime.fromtimestamp(expected, tz=UTC)


def test_read_pb_file() -> None:
    data = pb.read_pb_file("tests/samples/string_event.pb")
    assert data[0].val == "2015-01-08 19:47:01 UTC"
    assert data[0].timestamp.timestamp() == 1507712433.235971


def test_get_iso_timestamp_for_event_has_expected_output() -> None:
    event = ee.ScalarInt()
    event.secondsintoyear = 15156538
    event.nano = 381176001
    year = 2017
    expected = "2017-06-25T10:08:58.381176+00:00"
    assert pb.get_iso_timestamp_for_event(year, event) == expected


def test_read_sigma_file() -> None:
    data = pb.read_pb_file("tests/samples/sigma_test_pb.pb")
    assert "Sigma" in data[0].pv
    assert 0.11091079832009144 in np.array(data[0].val)
    assert data[0].year == 2023
    assert isinstance(data[0].val, list)
