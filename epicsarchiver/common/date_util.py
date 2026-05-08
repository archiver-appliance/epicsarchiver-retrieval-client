"""Utility functions for date formatting and validation."""

from __future__ import annotations

import datetime as _dt
from datetime import timedelta
from typing import TYPE_CHECKING

from pytz import UTC

from epicsarchiver.common.validation import ValidationError

if TYPE_CHECKING:
    import datetime

NANO_PER_SECOND = 1_000_000_000

MICRO_PER_SECOND = 1_000_000

NANO_PER_MICROSECOND = 1_000

EPOCH = _dt.datetime(1970, 1, 1, tzinfo=UTC)


_DATE_FORMATS = [
    "%Y%m%d",
    "%Y%m%d %H:%M",
    "%Y%m%d %H:%M:%S",
    "%Y-%m-%d",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%dT%H:%M%z",
    "%Y-%m-%d %H:%M%z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d %H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%d %H:%M:%S.%f%z",
]


class DateFormatError(ValidationError):
    """Exception raised for invalid date formats."""

    def __init__(self, date_str: str) -> None:
        """Initialize the DateFormatError with a specific message.

        Args:
            date_str (str): The date string that caused the error.
        """
        super().__init__(f"Date '{date_str}' is not in a valid format.")


def ensure_utc(
    input_time: datetime.datetime,
) -> datetime.datetime:
    """Add UTC timezone if timezone missing, otherwise convert to UTC.

    Args:
        input_time (datetime.datetime): A timestamp object.

    Returns:
        datetime.datetime: A timestamp object with timezone set to UTC.
    """
    return (
        input_time.replace(tzinfo=UTC)
        if input_time.tzinfo is None
        else input_time.astimezone(UTC)
    )


def year_start_epoch_seconds(year: int) -> int:
    """Seconds from Unix epoch at the start of a given year.

    Args:
        year (int): year

    Returns:
        int: seconds from epoch of start of year.
    """
    return int(
        (_dt.datetime(year, 1, 1, tzinfo=UTC) - EPOCH).total_seconds(),
    )


def _parse_datetime_str(date_str: str) -> datetime.datetime:
    """Parse a date string using known formats.

    Args:
        date_str: A date/datetime string.

    Returns:
        datetime.datetime: UTC-aware datetime.

    Raises:
        DateFormatError: If the string cannot be parsed.
    """
    for fmt in _DATE_FORMATS:
        try:
            return ensure_utc(
                _dt.datetime.strptime(date_str, fmt),  # noqa: DTZ007
            )
        except ValueError:  # noqa: PERF203
            continue
    raise DateFormatError(date_str)


class QueryTimestamp:
    """A microsecond-precision UTC timestamp for archiver queries.

    Wraps a UTC-aware datetime. Used for the input flow: user
    string/datetime to archiver HTTP query parameter.
    """

    __slots__ = ("_dt",)

    def __init__(self, dt: datetime.datetime) -> None:
        """Create from a UTC-aware datetime.

        Args:
            dt: UTC-aware datetime
        """
        self._dt = dt

    @classmethod
    def from_input(cls, date_or_str: datetime.datetime | str) -> QueryTimestamp:
        """Parse user input (string or datetime).

        Strings are parsed using a set of known formats.
        Strings without timezone information are treated as UTC.
        Datetimes are normalised to UTC.

        Args:
            date_or_str: A datetime object or a date/datetime string.

        Returns:
            QueryTimestamp
        """
        if isinstance(date_or_str, str):
            return cls(_parse_datetime_str(date_or_str))
        return cls(ensure_utc(date_or_str))

    @classmethod
    def from_datetime(cls, dt: datetime.datetime) -> QueryTimestamp:
        """From a datetime (naive assumed UTC, aware converted).

        Args:
            dt: A datetime object.

        Returns:
            QueryTimestamp
        """
        return cls(ensure_utc(dt))

    @property
    def datetime(self) -> datetime.datetime:
        """UTC-aware datetime.

        Returns:
            datetime.datetime: UTC datetime
        """
        return self._dt

    def to_query_string(self) -> str:
        """ISO 8601 with 'Z' suffix for archiver HTTP params.

        Returns:
            str: e.g. '2018-07-04T13:00:00.000000Z'
        """
        dt = self._dt.replace(tzinfo=None)
        return dt.isoformat(timespec="microseconds") + "Z"


class ResponseTimestamp:
    """A nanosecond-precision UTC timestamp from archiver responses.

    Internal representation is nanoseconds since Unix epoch (int).
    Used for the response flow: archiver data to datetime or
    display string. Precision is only lost when outputting to
    datetime (microsecond resolution).
    """

    __slots__ = ("_ns",)

    def __init__(self, timestamp_ns: int) -> None:
        """Create from nanosecond epoch timestamp.

        Args:
            timestamp_ns (int): nanoseconds since Unix epoch
        """
        self._ns = timestamp_ns

    @classmethod
    def from_yearsecondnanos(
        cls, year: int, seconds: int, nanos: int
    ) -> ResponseTimestamp:
        """From archiver PB format.

        Full nanosecond precision is preserved.

        Args:
            year (int): year
            seconds (int): seconds into year
            nanos (int): nanoseconds

        Returns:
            ResponseTimestamp
        """
        year_start = year_start_epoch_seconds(year)
        total_ns = (year_start + seconds) * NANO_PER_SECOND + nanos
        return cls(total_ns)

    @property
    def ns(self) -> int:
        """Nanoseconds since Unix epoch. Full precision.

        Returns:
            int: nanoseconds since epoch
        """
        return self._ns

    @property
    def datetime(self) -> datetime.datetime:
        """UTC-aware datetime (microsecond precision).

        Sub-microsecond nanoseconds are truncated.

        Returns:
            datetime.datetime: UTC datetime
        """
        return EPOCH + timedelta(
            microseconds=self._ns // NANO_PER_MICROSECOND,
        )

    def to_local_string(self) -> str:
        """Local timezone string for display.

        Returns:
            str: local timezone datetime string
        """
        return str(self.datetime.astimezone())
