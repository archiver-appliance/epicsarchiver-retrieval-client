"""Archive Event module for the ArchiveEvent class."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime as pydt

import pandas as pd
from pandas import Timestamp
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
    def timestamp(self) -> pydt:
        """Provides a datetime for the archive event.

        This will lose information (the last few decimal places) since
        datetime does not handle nano seconds.

        Returns:
            datetime: datetime for event
        """
        return self.pd_timestamp.to_pydatetime(warn=True)

    @property
    def pd_timestamp(self) -> Timestamp:
        """Provides a pandas Timestamp for the archive event.

        Returns:
            datetime: datetime for event
        """
        return ysn_timestamp(self.year, self.secondsintoyear, self.nanos)

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


def ysn_timestamp(year: int, seconds: int, nanos: int) -> Timestamp:
    """Get datetime from year, seconds into year and nanoseconds.

    Args:
        year (int): year
        seconds (int): seconds into year
        nanos (int): nanoseconds

    Returns:
        Timestamp: datetime
    """
    year_start = year_timestamp(year)

    return Timestamp((year_start + seconds) * int(1e9) + nanos, tz=UTC)


def dataframe_from_events(events: list[ArchiveEvent]) -> pd.DataFrame:
    """Converts a list of ArchiveEvent to pd.DataFrame.

    Args:
        events (list[ArchiveEvent]): input events

    Returns:
        pd.DataFrame: Output dataframe with columns "date", "val"
          where "date" is index column.
    """
    val = pd.DataFrame([event.__dict__ for event in events])
    val["date"] = [v.pd_timestamp for v in events]
    val = val[["date", "val"]]
    return val.set_index("date")
