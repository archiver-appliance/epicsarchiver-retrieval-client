"""Utility functions for date formatting and validation."""

from __future__ import annotations

import datetime as _dt
from typing import TYPE_CHECKING

from pytz import UTC

from epicsarchiver.common.validation import ValidationError

if TYPE_CHECKING:
    import datetime


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


def datetime_from_str(date_or_str: datetime.datetime | str) -> datetime.datetime:
    """Parse a date string or normalise a datetime object to a UTC-aware datetime.

    If the input is a string, it is parsed using a set of known formats.
    Strings without timezone information are treated as UTC.
    Strings with timezone information are converted to UTC.

    If the input is already a datetime object it is normalised to UTC using
    the same rules (naive → UTC, aware → converted to UTC).

    Args:
        date_or_str: A datetime object or a date/datetime string.

    Returns:
        datetime.datetime: UTC-aware datetime object.

    Raises:
        DateFormatError: If the string cannot be parsed into a datetime object.
    """
    if isinstance(date_or_str, str):
        for fmt in _DATE_FORMATS:
            try:
                return set_timezone_utc(_dt.datetime.strptime(date_or_str, fmt))  # noqa: DTZ007
            except ValueError:  # noqa: PERF203
                continue
        raise DateFormatError(date_or_str)
    return set_timezone_utc(date_or_str)


def format_date(at: datetime.datetime) -> str:
    """Format a datetime object to a string in ISO 8601 format with UTC timezone.

    Naive datetimes are assumed to be UTC. Timezone-aware datetimes are
    converted to UTC before formatting.

    Args:
        at (datetime.datetime): The datetime object to format.

    Returns:
        str: Formatted date string in ISO 8601 format with 'Z' suffix.
    """
    utc = set_timezone_utc(at)
    return utc.replace(tzinfo=None).isoformat(timespec="microseconds") + "Z"


def set_timezone_utc(
    input_time: datetime.datetime,
) -> datetime.datetime:
    """Add UTC timezone if timezone missing, otherwise convert to UTC.

    Args:
        input_time (datetime.datetime): A timestamp object.

    Returns:
        input_time (datetime.datetime): A timestamp object with timezone set to UTC.
    """
    return (
        input_time.replace(tzinfo=UTC)
        if input_time.tzinfo is None
        else input_time.astimezone(UTC)
    )
