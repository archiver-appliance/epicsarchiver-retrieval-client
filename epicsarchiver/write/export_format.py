"""Export format writers for machine-readable output of archived events."""

from __future__ import annotations

from enum import Enum, auto
from typing import IO, TYPE_CHECKING, Any

if TYPE_CHECKING:
    from epicsarchiver.retrieval.archive_event import ArchiveEvent, ArchiveEventsMeta


class Format(Enum):
    """Supported machine-readable output formats for the export command."""

    JSON = auto()
    CSV = auto()
    ARROW = auto()
    PARQUET = auto()
    PB = auto()


def write_events(
    dest: IO[Any],
    fmt: Format,
    events: list[ArchiveEvent],
    meta: dict[int, ArchiveEventsMeta] | None,
) -> None:
    """Write events to dest in the given format. Requires the [polars] extra.

    Args:
        dest: Binary destination to write to.
        fmt: Output format (JSON, CSV, ARROW, or PARQUET).
        events: Events to write.
        meta: Optional per-year metadata.

    Raises:
        ValueError: If fmt is not a supported event format (e.g. PB).
    """
    from epicsarchiver.retrieval.dataframe import dataframe_from_events  # noqa: PLC0415

    df = dataframe_from_events(events, meta or {})
    match fmt:
        case Format.CSV:
            import json  # noqa: PLC0415

            import polars as pl  # noqa: PLC0415

            # CSV doesn't support nested types; stringify list-of-struct columns
            df.with_columns(
                pl.Series(
                    "field_values",
                    [json.dumps(v) for v in df["field_values"].to_list()],
                    dtype=pl.String,
                ),
                pl.Series(
                    "headers",
                    [json.dumps(v) for v in df["headers"].to_list()],
                    dtype=pl.String,
                ),
            ).write_csv(dest)
        case Format.JSON:
            df.write_json(dest)  # type: ignore[call-overload]
        case Format.ARROW:
            df.write_ipc(dest)
        case Format.PARQUET:
            df.write_parquet(dest)
        case _:
            msg = f"Unsupported format for write_events: {fmt}"
            raise ValueError(msg)
