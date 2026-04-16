"""Polars DataFrame utilities for archived events.

Requires the [polars] extra: pip install py-epicsarchiver[polars]
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import polars as pl

from epicsarchiver.common.date_util import NS_PER_S

if TYPE_CHECKING:
    from epicsarchiver.retrieval.archive_event import (
        ArchiveEvent,
        ArchiveEventsMeta,
        FieldValue,
    )

_FIELD_VALUE_DTYPE = pl.List(pl.Struct({"name": pl.Utf8, "value": pl.Utf8}))


def _fv_list(fvs: list[FieldValue] | None) -> list[dict[str, str]]:
    return [{"name": fv.name, "value": fv.value} for fv in (fvs or [])]


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
    return pl.DataFrame({
        "date": pl.Series(
            [e.timestamp_ns for e in events], dtype=pl.Datetime("ns", "UTC")
        ),
        "val": [e.val for e in events],
        "severity": pl.Series([e.severity for e in events], dtype=pl.Int32),
        "status": pl.Series([e.status for e in events], dtype=pl.Int32),
        "field_values": pl.Series(
            [_fv_list(e.field_values) for e in events],
            dtype=_FIELD_VALUE_DTYPE,
        ),
        "headers": pl.Series(
            [
                _fv_list(meta[e.year].headers if e.year in meta else None)
                for e in events
            ],
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
    total_nanos = df["secs"].cast(pl.Int64) * NS_PER_S + df["nanos"].cast(pl.Int64)
    return df.with_columns(
        total_nanos.cast(pl.Datetime("ns", "UTC")).alias("date")
    ).drop(["secs", "nanos"])
