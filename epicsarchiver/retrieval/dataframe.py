"""Polars DataFrame utilities for archived events.

Requires the [polars] extra: pip install epicsarchiver-retrieval-client[polars]
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import polars as pl

from epicsarchiver.common.date_util import NANO_PER_SECOND

if TYPE_CHECKING:
    from collections.abc import Sequence

    from epicsarchiver.retrieval.archive_event import (
        ArchiveEvent,
        ArchiveEventsMeta,
        FieldValue,
    )

_FIELD_VALUE_DTYPE = pl.List(pl.Struct({"name": pl.Utf8, "value": pl.Utf8}))


def _field_value_column(
    field_value_lists: Sequence[Sequence[FieldValue] | None],
) -> pl.Series:
    """Build a list-of-struct column.

    Returns:
        A Polars list-of-struct Series with one value for each input list.
    """
    event_indices: list[int] = []
    names: list[str] = []
    values: list[str] = []
    for event_index, field_values in enumerate(field_value_lists):
        for field_value in field_values or []:
            event_indices.append(event_index)
            names.append(field_value.name)
            values.append(field_value.value)

    if not event_indices:
        return pl.repeat(
            pl.lit([], dtype=_FIELD_VALUE_DTYPE),
            len(field_value_lists),
            eager=True,
        )

    grouped_field_values = (
        pl
        .DataFrame({
            "event_index": event_indices,
            "name": names,
            "value": values,
        })
        .group_by("event_index", maintain_order=True)
        .agg(pl.struct("name", "value").alias("field_values"))
    )
    return (
        pl
        .DataFrame({
            "event_index": pl.Series(
                range(len(field_value_lists)),
                dtype=pl.Int64,
            )
        })
        .join(grouped_field_values, on="event_index", how="left")
        .get_column("field_values")
        .fill_null(pl.lit([], dtype=_FIELD_VALUE_DTYPE))
    )


@dataclass
class _EventColumns:
    date: list[int]
    pv: list[str]
    val: list[Any]
    severity: list[int]
    status: list[int]
    field_values: list[list[FieldValue] | None]
    headers: list[list[FieldValue]]

    @staticmethod
    def from_list(
        events: list[ArchiveEvent], metadata: dict[int, ArchiveEventsMeta]
    ) -> _EventColumns:
        cached_headers = {yr: m.headers for yr, m in metadata.items()}
        date_column = []
        pv_column = []
        val_column = []
        severity_column = []
        status_column = []
        field_values_column = []
        headers_column = []
        for e in events:
            date_column.append(e.timestamp_ns)
            pv_column.append(e.pv)
            val_column.append(e.val)
            severity_column.append(e.severity)
            status_column.append(e.status)
            field_values_column.append(e.field_values)
            headers_column.append(cached_headers.get(e.year, []))
        return _EventColumns(
            date=date_column,
            pv=pv_column,
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
        pl.DataFrame: columns "date", "pv", "val", "severity", "status",
            "field_values", "headers".
    """
    if not events:
        return pl.DataFrame(
            schema={
                "date": pl.Datetime("ns", "UTC"),
                "pv": pl.Utf8,
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
        "pv": pl.Series(event_columns.pv, dtype=pl.Utf8),
        "val": event_columns.val,
        "severity": pl.Series(event_columns.severity, dtype=pl.Int32),
        "status": pl.Series(event_columns.status, dtype=pl.Int32),
        "field_values": _field_value_column(event_columns.field_values),
        "headers": _field_value_column(event_columns.headers),
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
