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
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
from pandas import Timestamp

from epicsarchiver.retrieval import EPICSEvent_pb2 as ee
from epicsarchiver.retrieval.archive_event import (
    ArchiveEvent,
    FieldValue,
    ysn_timestamp,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime as pydt

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


ESC_BYTE = b"\x1b"
NL_BYTE = b"\x0a"
CR_BYTE = b"\x0d"

# The character sequences required to unescape & escape AA pb file format.
# Note that we need to be careful about the ordering here. We must apply them
# in the opposite order when escaping and unescaping. In particular, the
# escape byte needs to be escaped *first* and unescaped *last* in order to
# prevent extra bytes appearing and causing problems. See #59.
PB_REPLACEMENTS_ESCAPING = collections.OrderedDict([
    (ESC_BYTE + b"\x01", ESC_BYTE),
    (ESC_BYTE + b"\x02", NL_BYTE),
    (ESC_BYTE + b"\x03", CR_BYTE),
])
PB_REPLACEMENTS_UNESCAPING = collections.OrderedDict([
    (ESC_BYTE + b"\x03", CR_BYTE),
    (ESC_BYTE + b"\x02", NL_BYTE),
    (ESC_BYTE + b"\x01", ESC_BYTE),
])

EeScalarEvent = (
    ee.ScalarString
    | ee.ScalarShort
    | ee.ScalarFloat
    | ee.ScalarEnum
    | ee.ScalarByte
    | ee.ScalarInt
    | ee.ScalarDouble
)
EeVectorEvent = (
    ee.VectorString
    | ee.VectorShort
    | ee.VectorFloat
    | ee.VectorEnum
    | ee.VectorChar
    | ee.VectorInt
    | ee.VectorDouble
    | ee.V4GenericBytes
)
EeEvent = EeScalarEvent | EeVectorEvent


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


def event_pd_timestamp(
    year: int,
    event: EeEvent,
) -> Timestamp:
    """Converts from protobuf event time format to python datetime.

    Args:
        year (int): year of event
        event (EeEvent): input event

    Returns:
        pydt: Output datetime
    """
    return ysn_timestamp(year, event.secondsintoyear, event.nano)


def event_timestamp(
    year: int,
    event: EeEvent,
) -> pydt:
    """Converts from protobuf event time format to python datetime.

    Args:
        year (int): year of event
        event (EeEvent): input event

    Returns:
        pydt: Output datetime
    """
    return event_pd_timestamp(year, event).to_pydatetime()


def get_timestamp_from_line_function(
    chunk_info: ee.PayloadInfo,
) -> Callable[[bytes], pydt]:
    """From a unescaped protobuf line create a function to get datetime.

    Args:
        chunk_info (ee.PayloadInfo): Payload info of protobuf file

    Returns:
        Callable[[bytes], pydt]: Function to provide event time
    """

    def timestamp_from_line(line: bytes) -> pydt:
        event = TYPE_MAPPINGS[chunk_info.type]()
        event.ParseFromString(unescape_bytes(line))
        return event_timestamp(
            chunk_info.year,
            event,  # pylint: disable=no-member
        )

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
    log.debug("%s chunks in pb file", len(chunks))
    year_chunks: OrderedDict[int, tuple[ee.PayloadInfo, list[bytes]]] = (
        collections.OrderedDict()
    )
    for chunk in chunks:
        lines = chunk.split(b"\n")
        chunk_info = ee.PayloadInfo()
        chunk_info.ParseFromString(unescape_bytes(lines[0]))
        chunk_year = chunk_info.year  # pylint: disable=no-member
        log.debug("Year %s: %s events in chunk", chunk_year, len(lines) - 1)
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
    val = event.val
    if isinstance(
        event,
        ee.VectorDouble
        | ee.VectorEnum
        | ee.VectorFloat
        | ee.VectorInt
        | ee.VectorShort
        | ee.VectorString,
    ):
        vector_val = list(val)
        val = vector_val
    return ArchiveEvent(
        pv,
        val,
        event.secondsintoyear,
        year,
        event.nano,
        event.severity,
        event.status,
        [to_field_value(f) for f in event.fieldvalues],
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
        events += [
            _event_from_line(line, chunk_info.pvname, year, chunk_info.type)
            for line in lines
        ]

    return events


def get_iso_timestamp_for_event(
    year: int,
    event: EeEvent,
) -> str:
    """Returns an ISO-formatted timestamp string for the given event."""
    return pd.Timestamp(event_timestamp(year, event)).isoformat()


def read_pb_file(filename: str) -> list[ArchiveEvent]:
    """Read an unescaped protobuf file and produce a list of events from file.

    Args:
        filename (str): location of file

    Returns:
        list[ArchiveEvent]: list of events in file
    """
    raw_data = bytearray()
    raw_data.extend(Path(filename).read_bytes())

    return parse_pb_data(raw_data)


def to_field_value(f: ee.FieldValue) -> FieldValue:
    """From the protobuf variant.

    Args:
        f (ee.FieldValue): protobuf field value

    Returns:
        FieldValue: Basic Field Value
    """
    return FieldValue(f.name, f.val)
