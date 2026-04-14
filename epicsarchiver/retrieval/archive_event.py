"""Archive Event module for the ArchiveEvent class."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime as pydt
from datetime import timedelta

from pytz import utc as UTC  # noqa: N812


@dataclass
class FieldValue:
    """Basic representation of a changed field value from an archive event.

    Returns:
        FieldValue: Pair of name and value
    """

    name: str | None
    value: str | None


@dataclass
class ArchiveEventsMeta:
    """Metadata about a year's chunk of archived events."""

    pv_name: str
    pv_type: str
    element_count: int
    headers: list[FieldValue]
    year: int


ArchiveEventsData = tuple[dict[int, ArchiveEventsMeta], list["ArchiveEvent"]]


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
    field_values: list[FieldValue] | None

    @property
    def timestamp_ns(self) -> int:
        """Nanoseconds since Unix epoch.

        Returns:
            int: nanoseconds since Unix epoch, compatible with pl.Datetime("ns", "UTC")
        """
        return (
            year_timestamp(self.year) + self.secondsintoyear
        ) * 1_000_000_000 + self.nanos

    @property
    def timestamp(self) -> pydt:
        """UTC datetime (microsecond precision), derived from timestamp_ns.

        Returns:
            datetime: UTC datetime
        """
        return pydt(1970, 1, 1, tzinfo=UTC) + timedelta(
            microseconds=self.timestamp_ns // 1_000
        )

    @property
    def field_values_dict(self) -> dict[str, str]:
        """Provides a dict of field values.

        Returns:
            dict[str, str]: dict of field names and values
        """
        if not self.field_values:
            return {}
        return {
            field.name: field.value or "" for field in self.field_values if field.name
        }


def year_timestamp(year: int) -> int:
    """Generates int timestamp for number of seconds from unix epoch at start of year.

    Args:
        year (int): year

    Returns:
        int: seconds from epoch of start of year.
    """
    return int(
        (pydt(year, 1, 1, tzinfo=UTC) - pydt(1970, 1, 1, tzinfo=UTC)).total_seconds(),
    )


def ysn_timestamp(year: int, seconds: int, nanos: int) -> pydt:
    """Get datetime from year, seconds into year and nanoseconds.

    Precision is truncated to microseconds.

    Args:
        year (int): year
        seconds (int): seconds into year
        nanos (int): nanoseconds

    Returns:
        datetime: UTC datetime (microsecond precision)
    """
    year_start = year_timestamp(year)
    total_us = (year_start + seconds) * 1_000_000 + nanos // 1_000
    return pydt(1970, 1, 1, tzinfo=UTC) + timedelta(microseconds=total_us)
