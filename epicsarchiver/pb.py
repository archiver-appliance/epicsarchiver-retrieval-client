"""Handle retrieval of data in the Archiver Appliance PB file format.

The file format is described on this page:
https://slacmshankar.github.io/epicsarchiver_docs/pb_pbraw.html

The data can be parsed in the same way whether retrieved using the
Rest API or whether reading files directly from disk. In either
case, it is important to treat the data as binary data - a stream of
bytes. The Google Protobuf library handles converting the stream of
bytes into the objects defined by the EPICSEvent.proto file.

The Archiver Appliance escapes certain characters as described on the
page above, which allows one to deduce the number of events in the
binary file using tools such as wc.

The unescape_bytes() method handles unescaping these characters before
handing the interpretation over to the Google Protobuf library.

Note: due to the way the protobuf objects are constructed, pylint can't
correctly deduce some properties, so I have manually disabled some warnings.

"""
from __future__ import annotations

import collections
import logging as log
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime as dt
from typing import cast

import pandas as pd
from pytz import utc as UTC  # noqa: N812

from epicsarchiver import EPICSEvent_pb2 as ee

# It is not clear to me why I can't extract this information
# from the compiled protobuf file.
TYPE_MAPPINGS: dict[int, type] = {
    0: ee.ScalarString,
    1: ee.ScalarShort,
    2: ee.ScalarFloat,
    3: ee.ScalarEnum,
    4: ee.ScalarByte,
    5: ee.ScalarInt,
    6: ee.ScalarDouble,
    7: ee.VectorString,
    8: ee.VectorShort,
    9: ee.VectorFloat,
    10: ee.VectorEnum,
    11: ee.VectorChar,
    12: ee.VectorInt,
    13: ee.VectorDouble,
    14: ee.V4GenericBytes,
}


INVERSE_TYPE_MAPPINGS = {cls: numeric for numeric, cls in TYPE_MAPPINGS.items()}


ESC_BYTE = b"\x1B"
NL_BYTE = b"\x0A"
CR_BYTE = b"\x0D"

# The character sequences required to unescape & escape AA pb file format.
# Note that we need to be careful about the ordering here. We must apply them
# in the opposite order when escaping and unescaping. In particular, the
# escape byte needs to be escaped *first* and unescaped *last* in order to
# prevent extra bytes appearing and causing problems. See #59.
PB_REPLACEMENTS_ESCAPING = collections.OrderedDict(
    [
        (ESC_BYTE + b"\x01", ESC_BYTE),
        (ESC_BYTE + b"\x02", NL_BYTE),
        (ESC_BYTE + b"\x03", CR_BYTE),
    ]
)
PB_REPLACEMENTS_UNESCAPING = collections.OrderedDict(
    [
        (ESC_BYTE + b"\x03", CR_BYTE),
        (ESC_BYTE + b"\x02", NL_BYTE),
        (ESC_BYTE + b"\x01", ESC_BYTE),
    ]
)


@dataclass
class ArchiveEvent:
    """One Event, retrieved from the AA, representing a change in value of a PV."""

    pv: str
    val: int | float | str | list[str] | list[int] | list[float] | bytes
    secondsintoyear: int
    year: int
    nanos: int
    severity: int
    status: int
    field_values: list[ee.FieldValue]

    @property
    def timestamp(self) -> dt:
        """Provides a datetime for the archive event.

        Returns:
            datetime: datetime for event
        """
        return ysn_timestamp(self.year, self.secondsintoyear, self.nanos)

    def _pb_event(
        self,
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
                self (ArchiveEvent): An Archive Event to convert

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
        if isinstance(self.val, int):
            return ee.ScalarInt(
                secondsintoyear=self.secondsintoyear,
                nano=self.nanos,
                val=self.val,
                severity=self.severity,
                status=self.status,
                fieldvalues=self.field_values,
            )
        if isinstance(self.val, float):
            return ee.ScalarDouble(
                secondsintoyear=self.secondsintoyear,
                nano=self.nanos,
                val=self.val,
                severity=self.severity,
                status=self.status,
                fieldvalues=self.field_values,
            )
        if isinstance(self.val, str):
            return ee.ScalarString(
                secondsintoyear=self.secondsintoyear,
                nano=self.nanos,
                val=self.val,
                severity=self.severity,
                status=self.status,
                fieldvalues=self.field_values,
            )
        if isinstance(self.val, bytes):
            return ee.V4GenericBytes(
                secondsintoyear=self.secondsintoyear,
                nano=self.nanos,
                val=self.val,
                severity=self.severity,
                status=self.status,
                fieldvalues=self.field_values,
            )
        if all(isinstance(x, str) for x in self.val):
            return ee.VectorString(
                secondsintoyear=self.secondsintoyear,
                nano=self.nanos,
                val=self.val,  # type: ignore
                severity=self.severity,
                status=self.status,
                fieldvalues=self.field_values,
            )
        if all(isinstance(x, int) for x in self.val):
            return ee.VectorInt(
                secondsintoyear=self.secondsintoyear,
                nano=self.nanos,
                val=self.val,  # type: ignore
                severity=self.severity,
                status=self.status,
                fieldvalues=self.field_values,
            )
        if all(isinstance(x, float) for x in self.val):
            return ee.VectorFloat(
                secondsintoyear=self.secondsintoyear,
                nano=self.nanos,
                val=self.val,  # type: ignore
                severity=self.severity,
                status=self.status,
                fieldvalues=self.field_values,
            )
        return ee.VectorString(
            secondsintoyear=self.secondsintoyear,
            nano=self.nanos,
            val=None,
            severity=self.severity,
            status=self.status,
            fieldvalues=self.field_values,
        )


def dataframe_from_events(events: list[ArchiveEvent]) -> pd.DataFrame:
    """Converts a list of ArchiveEvent to pd.DataFrame.

    Args:
        events (list[ArchiveEvent]): input events

    Returns:
        pd.DataFrame: Output dataframe with columns "date", "val"
          where "date" is index column.
    """
    val = cast(pd.DataFrame, pd.DataFrame([event.__dict__ for event in events]))
    val["date"] = [
        pd.Timestamp(
            (year_timestamp(v.year) + v.secondsintoyear) * 1e9 + v.nanos, tz=UTC
        )
        for v in events
    ]
    val = val[["date", "val"]]
    val = val.set_index("date")
    return val


def unescape_bytes(byte_seq: bytes) -> bytes:
    """Replace specific sub-sequences in a bytes sequence.

    This escaping is defined as part of the Archiver Appliance raw file
    format: https://slacmshankar.github.io/epicsarchiver_docs/pb_pbraw.html

    Args:
        byte_seq: any byte sequence
    Returns:
        the byte sequence unescaped according to the AA file format rules
    """
    for key, value in PB_REPLACEMENTS_UNESCAPING.items():
        byte_seq = byte_seq.replace(key, value)
    return bytes(byte_seq)


def escape_bytes(byte_seq: bytes) -> bytes:
    """Replace specific sub-sequences in a bytes sequence.

    This escaping is defined as part of the Archiver Appliance raw file
    format: https://slacmshankar.github.io/epicsarchiver_docs/pb_pbraw.html

    Args:
        byte_seq: any byte sequence
    Returns:
        the byte sequence escaped according to the AA file format rules
    """
    for key, value in PB_REPLACEMENTS_ESCAPING.items():
        byte_seq = byte_seq.replace(value, key)
    return byte_seq


def year_timestamp(year: int) -> float:
    """Generates float timestamp for number of seconds from unix epoch at start of year.

    Args:
        year (int): year

    Returns:
        float: seconds from epoch of start of year.
    """
    return (dt(year, 1, 1, tzinfo=UTC) - dt(1970, 1, 1, tzinfo=UTC)).total_seconds()


def event_timestamp(  # noqa: D417
    year: int,
    event: ee.ScalarString
    | ee.ScalarShort
    | ee.ScalarFloat
    | ee.ScalarEnum
    | ee.ScalarByte
    | ee.ScalarInt
    | ee.ScalarDouble
    | ee.VectorString
    | ee.VectorShort
    | ee.VectorFloat
    | ee.VectorEnum
    | ee.VectorChar
    | ee.VectorInt
    | ee.VectorDouble
    | ee.V4GenericBytes,
) -> dt:
    """Converts from protobuf event time format to python datetime.

    Args:
        year (int): year of event
        event (ee.ScalarString
        | ee.ScalarShort
        | ee.ScalarFloat
        | ee.ScalarEnum
        | ee.ScalarByte
        | ee.ScalarInt
        | ee.ScalarDouble
        | ee.VectorString
        | ee.VectorShort
        | ee.VectorFloat
        | ee.VectorEnum
        | ee.VectorChar
        | ee.VectorInt
        | ee.VectorDouble
        | ee.V4GenericBytes): input event

    Returns:
        dt: Output datetime
    """
    return ysn_timestamp(year, event.secondsintoyear, event.nano)


def ysn_timestamp(year: int, seconds: int, nanos: int) -> dt:
    """Get datetime from year, seconds into year and nanoseconds.

    Args:
        year (int): year
        seconds (int): seconds into year
        nanos (int): nanoseconds

    Returns:
        dt: datetime
    """
    year_start = year_timestamp(year)

    # This will lose information (the last few decimal places) since
    # a double cannot store 18 significant figures.
    return dt.fromtimestamp(year_start + seconds + 1e-9 * nanos, tz=UTC)


def get_timestamp_from_line_function(
    chunk_info: ee.PayloadInfo,
) -> Callable[[bytes], dt]:
    """From a unescaped protobuf line create a function to get datetime.

    Args:
        chunk_info (ee.PayloadInfo): Payload info of protobuf file

    Returns:
        Callable[[bytes], dt]: Function to provide event time
    """

    def timestamp_from_line(line: bytes) -> dt:
        event = TYPE_MAPPINGS[chunk_info.type]()
        event.ParseFromString(unescape_bytes(line))
        event_time = event_timestamp(
            chunk_info.year, event  # pylint: disable=no-member
        )
        return event_time

    return timestamp_from_line


def _break_up_chunks(
    raw_data: bytes,
) -> OrderedDict[int, tuple[ee.PayloadInfo, list[bytes]]]:
    """Break up raw data into chunks by year.

    Args:
        raw_data: Raw data from file

    Returns:
        collections.OrderedDict: keys are years; values are lists of chunks
    """
    chunks = [chunk.strip() for chunk in raw_data.split(b"\n\n")]
    log.debug(f"{len(chunks)} chunks in pb file")
    year_chunks: OrderedDict[
        int, tuple[ee.PayloadInfo, list[bytes]]
    ] = collections.OrderedDict()
    for chunk in chunks:
        lines = chunk.split(b"\n")
        chunk_info = ee.PayloadInfo()
        chunk_info.ParseFromString(unescape_bytes(lines[0]))
        chunk_year = chunk_info.year  # pylint: disable=no-member
        log.debug(f"Year {chunk_year}: {len(lines) - 1} events in chunk")
        try:
            _, ls = year_chunks[chunk_year]
            ls.extend(lines[1:])
        except KeyError:
            year_chunks[chunk_year] = chunk_info, lines[1:]
    return year_chunks


def _event_from_line(line: bytes, pv: str, year: int, event_type: int) -> ArchiveEvent:
    """Get an ArchiveEvent from this line.

    Args:
        line: A line of chunks of data
        pv: Name of the PV
        year: Year of interest
        event_type: Need to know the type of the event as key of TYPE_MAPPINGS

    Returns:
        ArchiveEvent
    """
    unescaped = unescape_bytes(line)
    event = TYPE_MAPPINGS[event_type]()
    event.ParseFromString(unescaped)
    return ArchiveEvent(
        pv,
        event.val,
        event.secondsintoyear,
        year,
        event.nano,
        event.severity,
        event.status,
        event.fieldvalues,
    )


def parse_pb_data(raw_data: bytes) -> list[ArchiveEvent]:
    """Turn raw PB data into an ArchiveData object.

    Args:
        raw_data: The raw data

    Returns:
        An ArchiveData object
    """
    year_chunks = _break_up_chunks(raw_data)
    events: list[ArchiveEvent] = []
    # Iterate over years
    for year, (chunk_info, lines) in year_chunks.items():
        for line in lines:
            events.append(
                _event_from_line(line, chunk_info.pvname, year, chunk_info.type)
            )

    return events


def get_iso_timestamp_for_event(
    year: int,
    event: ee.ScalarString
    | ee.ScalarShort
    | ee.ScalarFloat
    | ee.ScalarEnum
    | ee.ScalarByte
    | ee.ScalarInt
    | ee.ScalarDouble
    | ee.VectorString
    | ee.VectorShort
    | ee.VectorFloat
    | ee.VectorEnum
    | ee.VectorChar
    | ee.VectorInt
    | ee.VectorDouble
    | ee.V4GenericBytes,
) -> str:
    """Returns an ISO-formatted timestamp string for the given event."""
    return event_timestamp(year, event).isoformat()


def read_pb_file(filename: str) -> list[ArchiveEvent]:
    """Read an unescaped protobuf file and produce a list of events from file.

    Args:
        filename (str): location of file

    Returns:
        list[ArchiveEvent]: list of events in file
    """
    with open(filename, "rb") as f:
        raw_data = bytearray()
        raw_data.extend(f.read())

        return parse_pb_data(raw_data)


def create_pb_bytes(  # noqa: D417
    events: list[ee.ScalarString]
    | list[ee.ScalarShort]
    | list[ee.ScalarFloat]
    | list[ee.ScalarEnum]
    | list[ee.ScalarByte]
    | list[ee.ScalarInt]
    | list[ee.ScalarDouble]
    | list[ee.VectorString]
    | list[ee.VectorShort]
    | list[ee.VectorFloat]
    | list[ee.VectorEnum]
    | list[ee.VectorChar]
    | list[ee.VectorInt]
    | list[ee.VectorDouble]
    | list[ee.V4GenericBytes],
    info: ee.PayloadInfo,
) -> bytes:
    """Mostly used for testing, converts list of events to escaped protobuf bytes.

    Args:
        events (list[ee.ScalarString]
        | list[ee.ScalarShort]
        | list[ee.ScalarFloat]
        | list[ee.ScalarEnum]
        | list[ee.ScalarByte]
        | list[ee.ScalarInt]
        | list[ee.ScalarDouble]
        | list[ee.VectorString]
        | list[ee.VectorShort]
        | list[ee.VectorFloat]
        | list[ee.VectorEnum]
        | list[ee.VectorChar]
        | list[ee.VectorInt]
        | list[ee.VectorDouble]
        | list[ee.V4GenericBytes]): list of events
        info (ee.PayloadInfo): payload data

    Returns:
        bytes: escaped bytes
    """
    info_bytes = escape_bytes(info.SerializeToString())
    events_bytes = b"\n".join(escape_bytes(e.SerializeToString()) for e in events)
    return info_bytes + b"\n" + events_bytes
