"""Archive Event module for the ArchiveEvent class."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from epicsarchiver.common.date_util import (
    NS_PER_S,
    ns_to_datetime,
    year_timestamp,
)

if TYPE_CHECKING:
    from datetime import datetime


@dataclass
class FieldValue:
    """Basic representation of a changed field value from an archive event.

    Returns:
        FieldValue: Pair of name and value
    """

    name: str
    value: str


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
        ) * NS_PER_S + self.nanos

    @property
    def timestamp(self) -> datetime:
        """UTC datetime (microsecond precision), derived from timestamp_ns.

        Returns:
            datetime: UTC datetime
        """
        return ns_to_datetime(self.timestamp_ns)

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
