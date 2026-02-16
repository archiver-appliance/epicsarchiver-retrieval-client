"""Utility functions for date formatting and validation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from dateutil import parser
from pytz import UTC

from epicsarchiver.common.validation import ValidationError

if TYPE_CHECKING:
    import datetime


class DateFormatError(ValidationError):
    """Exception raised for invalid date formats."""

    def __init__(self, date_str: str) -> None:
        """Initialize the DateFormatError with a specific message.

        Args:
            date_str (str): The date string that caused the error.
        """
        super().__init__(f"Date '{date_str}' is not in a valid format.")


def datetime_from_str(date_or_str: datetime.datetime | str) -> datetime.datetime:
    """Formats a date or string to a datetime object.

    If the input is a string, it attempts to parse it into a datetime object.
    If the input is already a datetime object, it returns it without timezone info.

    All timezone information is stripped from the datetime object.

    Args:
        date_or_str: can be a datetime object or string

    Returns:
        datetime.datetime: datetime object without timezone info.

    Raises:
        DateFormatError: If the string cannot be parsed into a datetime object.
    """
    if isinstance(date_or_str, str):
        try:
            return parser.parse(date_or_str, ignoretz=True)
        except parser.ParserError as e:
            raise DateFormatError(date_or_str) from e
    return date_or_str.replace(tzinfo=None)


def format_date(at: datetime.datetime) -> str:
    """Format a datetime object to a string in ISO 8601 format with UTC timezone.

    Args:
        at (datetime.datetime): The datetime object to format.

    Returns:
        str: Formatted date string in ISO 8601 format with 'Z' suffix.
    """
    return at.replace(tzinfo=None).isoformat(timespec="microseconds") + "Z"


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
