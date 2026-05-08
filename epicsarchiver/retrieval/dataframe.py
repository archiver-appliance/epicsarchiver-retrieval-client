"""Polars DataFrame utilities for archived events.

Requires the [polars] extra: pip install py-epicsarchiver[polars]
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import polars as pl

from epicsarchiver.common.date_util import NANO_PER_SECOND

if TYPE_CHECKING:
    from epicsarchiver.retrieval.archive_event import (
        ArchiveEvent,
        ArchiveEventsMeta,
        FieldValue,
    )

_FIELD_VALUE_DTYPE = pl.List(pl.Struct({"name": pl.Utf8, "value": pl.Utf8}))


def _fv_list(fvs: list[FieldValue] | None) -> list[dict[str, str]]:
    return [{"name": fv.name, "value": fv.value} for fv in (fvs or [])]


@dataclass
class _EventColumns:
    date: list[int]
    val: list[Any]
    severity: list[int]
    status: list[int]
    field_values: list[list[dict[str, str]]]
    headers: list[list[dict[str, str]]]

    @staticmethod
    def from_list(
        events: list[ArchiveEvent], metadata: dict[int, ArchiveEventsMeta]
    ) -> _EventColumns:
        cached_headers: dict[int, list[dict[str, str]]] = {
            yr: _fv_list(m.headers) for yr, m in metadata.items()
        }
        date_column = []
        val_column = []
        severity_column = []
        status_column = []
        field_values_column = []
        headers_column = []
        for e in events:
            date_column.append(e.timestamp_ns)
            val_column.append(e.val)
            severity_column.append(e.severity)
            status_column.append(e.status)
            field_values_column.append(_fv_list(e.field_values))
            headers_column.append(cached_headers.get(e.year, []))
        return _EventColumns(
            date=date_column,
            val=val_column,
            severity=severity_column,
            status=status_column,
            field_values=field_values_column,
            headers=headers_column,
        )


def dataframe_from_events(
    events: list[ArchiveEvent],
    metadata: dict[int, ArchiveEventsMeta] | None = None,
) -> pl.DataFrame:
    """Converts a list of ArchiveEvent to pl.DataFrame.

    Args:
        events (list[ArchiveEvent]): input events
        metadata (dict[int, ArchiveEventsMeta] | None): optional per-year metadata;
            when provided, populates the "headers" column.

    Returns:
        pl.DataFrame: columns "date", "val", "severity", "status",
            "field_values", "headers".
    """
    if not events:
        return pl.DataFrame(
            schema={
                "date": pl.Datetime("ns", "UTC"),
                "val": pl.Null,
                "severity": pl.Int32,
                "status": pl.Int32,
                "field_values": _FIELD_VALUE_DTYPE,
                "headers": _FIELD_VALUE_DTYPE,
            }
        )
    meta = metadata or {}

    event_columns = _EventColumns.from_list(events, meta)

    return pl.DataFrame({
        "date": pl.Series(event_columns.date, dtype=pl.Datetime("ns", "UTC")),
        "val": event_columns.val,
        "severity": pl.Series(event_columns.severity, dtype=pl.Int32),
        "status": pl.Series(event_columns.status, dtype=pl.Int32),
        "field_values": pl.Series(
            event_columns.field_values,
            dtype=_FIELD_VALUE_DTYPE,
        ),
        "headers": pl.Series(
            event_columns.headers,
            dtype=_FIELD_VALUE_DTYPE,
        ),
    })


def json_to_dataframe(data: Any) -> pl.DataFrame:
    """Converts json from the archiver.

    Converts to a dataframe with columns "date", "val", and any other fields
    returned by the API (typically "severity", "status").

    Args:
        data: json from a json archiver request

    Returns:
        pl.DataFrame
    """
    raw = data[0]["data"]
    if not raw:
        return pl.DataFrame(
            schema={
                "date": pl.Datetime("ns", "UTC"),
                "val": pl.Null,
                "severity": pl.Int32,
                "status": pl.Int32,
            }
        )
    df = pl.DataFrame(raw)
    total_nanos = df["secs"].cast(pl.Int64) * NANO_PER_SECOND + df["nanos"].cast(
        pl.Int64
    )
    return df.with_columns(
        total_nanos.cast(pl.Datetime("ns", "UTC")).alias("date")
    ).drop(["secs", "nanos"])
