"""Data structures for the statistics endpoints from the archiver."""

import datetime
import enum
from dataclasses import dataclass

import pytz

from epicsarchiver.channelfinder import Channel


class DroppedReason(str, enum.Enum):
    """List of reasons why a PV could be dropping events.

    Includes the endpoints in the archiver corresponding to the reason.
    """

    IncorrectTimestamp = "/getPVsByDroppedEventsTimestamp"
    BufferOverflow = "/getPVsByDroppedEventsBuffer"
    TypeChange = "/getPVsByDroppedEventsTypeChange"
    SlowChanging = "/getSlowChangingPVsWithDroppedEvents"


@dataclass
class BaseStatResponse:
    """Base class for responses from the archiver statistical endpoints."""

    pv_name: str


@dataclass
class DroppedPVResponse(BaseStatResponse):
    """Response from the endpoints in DroppedReason."""

    events_dropped: int
    dropped_reason: DroppedReason

    @classmethod
    def from_json(
        cls,
        json: dict[str, str],
        dropped_reason: DroppedReason,
    ) -> "DroppedPVResponse":
        """Convert to DroppedPVResponse from dictionary generated from json.

        Args:
            json (dict[str, str]): Input json
            dropped_reason (DroppedReason): Input reason for events being dropped

        Returns:
            DroppedPVResponse: The corresponding DroppedPVResponse
        """
        return DroppedPVResponse(
            json["pvName"],
            int(json["eventsDropped"]),
            dropped_reason,
        )

    def __str__(self) -> str:
        """Generate a display string for the response.

        Returns:
            str: "Dropped {events} by {reason}"
        """
        return f"Dropped {self.events_dropped} events by {self.dropped_reason.name}"


# Different date formats depending on which api and version of the archiver
_DATE_FORMAT_OFFSET = "%b/%d/%Y %H:%M:%S %z"
_DATE_FORMAT_TIMEZONE = "%b/%d/%Y %H:%M:%S %Z"


def _parse_archiver_datetime(datetime_str: str) -> datetime.datetime | None:
    if datetime_str in {"Never", ""}:
        return None
    try:
        return datetime.datetime.strptime(datetime_str, _DATE_FORMAT_OFFSET).replace(
            tzinfo=pytz.utc
        )
    except ValueError:
        try:
            return datetime.datetime.strptime(
                datetime_str, _DATE_FORMAT_TIMEZONE
            ).replace(tzinfo=pytz.utc)
        except ValueError:
            return None


@dataclass
class DisconnectedPVsResponse(BaseStatResponse):
    """Response from getCurrentlyDisconnectedPVs.

    Example:

    .. code-block:: json

        {
            "hostName": "N/A",
            "connectionLostAt": "Sep/14/2023 16:00:18 +02:00",
            "pvName": "HCB-ACH:ODH-O2iM-1:O2Level",
            "instance": "sw-vm-11",
            "commandThreadID": "6",
            "noConnectionAsOfEpochSecs": "1694700018",
            "lastKnownEvent": "Aug/25/2023 15:38:17 +02:00"
        }
    """

    host_name: str
    connection_lost_at: datetime.datetime | None
    instance: str
    command_thread_id: int
    no_connection_as_of_epoch: int
    last_known_event: datetime.datetime | None

    @classmethod
    def from_json(cls, json: dict[str, str]) -> "DisconnectedPVsResponse":
        """Response from the endpoint in getCurrentlyDisconnectedPVs."""
        return DisconnectedPVsResponse(
            json["pvName"],
            json["hostName"],
            _parse_archiver_datetime(json["connectionLostAt"]),
            json["instance"],
            int(json["commandThreadID"]),
            int(json["noConnectionAsOfEpochSecs"]),
            _parse_archiver_datetime(json["lastKnownEvent"]),
        )

    def __str__(self) -> str:
        """Generate a display string for the response.

        Returns:
            str: "Disconnected {time_difference} ago. Last event at {last_known_event}"
        """
        if self.connection_lost_at:
            time_difference = str(
                datetime.datetime.now(tz=pytz.utc) - self.connection_lost_at,
            )
        else:
            time_difference = "Never"
        return (
            f"Disconnected {time_difference} ago. Last event at {self.last_known_event}"
        )


@dataclass
class SilentPVsResponse(BaseStatResponse):
    """Return a list of PVs sorted by the timestamp of the last event received.

    Example:

    .. code-block:: json

        {"pvName":"DTL-030:SC-IOC-002:CA_CLNT_CNT","instance":"archiver-linac-01","lastKnownEvent":"Never"}
    """

    instance: str
    last_known_event: datetime.datetime | None

    @classmethod
    def from_json(cls, json: dict[str, str]) -> "SilentPVsResponse":
        """Response from the endpoint in getSilentPVsReport."""
        return SilentPVsResponse(
            json["pvName"],
            json["instance"],
            _parse_archiver_datetime(json["lastKnownEvent"]),
        )

    def __str__(self) -> str:
        """Generate a display string for the response.

        Returns:
            str: "No events stored. Last invalid event recieved at {last_known_event}"
        """
        return (
            f"No events stored. Last invalid event recieved at {self.last_known_event}"
        )


class ConnectionStatus(enum.Enum):
    """Connection status enum.

    Args:
        enum (int): Placement of enum.
    """

    CurrentlyConnected = 1
    NotCurrentlyConnected = 2


@dataclass
class LostConnectionsResponse(BaseStatResponse):
    """Return a list of PVs sorted by the no. of connection drops.

    Example:

    .. code-block:: json

        {
            "currentlyConnected": "Yes",
            "pvName": "MBL-010LWU:Vac-VPN-10000:IonCurR",
            "instance": "archiver-linac-01",
            "lostConnections": "2586"
        }
    """

    currently_connected: ConnectionStatus
    instance: str
    lost_connections: int

    @classmethod
    def from_json(cls, json: dict[str, str]) -> "LostConnectionsResponse":
        """Response from the endpoint in getLostConnectionsReport."""
        return LostConnectionsResponse(
            json["pvName"],
            ConnectionStatus.CurrentlyConnected
            if json["currentlyConnected"] == "Yes"
            else ConnectionStatus.NotCurrentlyConnected,
            json["instance"],
            int(json["lostConnections"]),
        )

    def __str__(self) -> str:
        """Generate a display string for the response.

        Returns:
            str: "Lost connections: {lost_connections}. Connected: {connected}"
        """
        l_con = self.lost_connections
        cur_con = self.currently_connected
        return f"Lost connections: {l_con}. Connected: {cur_con}"


@dataclass
class StorageRatesResponse(BaseStatResponse):
    """Return a list of PVs sorted by the no. of connection drops.

    Example:

    .. code-block:: json

        {
            "pvName": "TS2-010CRM:EMR-XRS-001:mca1",
            "storageRate_MBperDay": "1099.2894956029622",
            "storageRate_KBperHour": "46903.01847905972",
            "storageRate_GBperYear": "391.8365877881653"
        }
    """

    mb_per_day: float
    kb_per_hour: float
    gb_per_year: float

    @classmethod
    def from_json(cls, json: dict[str, str]) -> "StorageRatesResponse":
        """Response from the endpoint in getStorageRateReport."""
        return StorageRatesResponse(
            json["pvName"],
            float(json["storageRate_MBperDay"]),
            float(json["storageRate_KBperHour"]),
            float(json["storageRate_GBperYear"]),
        )

    def __str__(self) -> str:
        """Generate a display string for the response.

        Returns:
            str: "Storing {self.mb_per_day} MB per day."
        """
        return f"Storing {self.mb_per_day} MB per day."


@dataclass
class BothArchiversResponse(BaseStatResponse):
    """Response of pvs archived in two archivers."""

    hostname: str
    other_hostname: str

    def __str__(self) -> str:
        """Generate a display string for the response.

        Returns:
            str: "In both {hostname} and {other_hostname}"
        """
        return f"In both {self.hostname} and {self.other_hostname}"


@dataclass
class PausedPVResponse(BaseStatResponse):
    """Response of pvs paused."""

    instance: str
    modification_time: str

    @classmethod
    def from_json(cls, json: dict[str, str]) -> "PausedPVResponse":
        """Response from the endpoint in getPausedPVsReport."""
        return PausedPVResponse(
            json["pvName"],
            json["instance"],
            json["modificationTime"],
        )

    def __str__(self) -> str:
        """Generate a display string for the response.

        Returns:
            str: "{pv} is paused"
        """
        return f"{self.pv_name} is paused"


class ConfiguredStatus(enum.Enum):
    """Represents if a pv is configured or archived."""

    Archived = 1
    Configured = 2


@dataclass
class NoConfigResponse(BaseStatResponse):
    """Response of pvs archived but not in configuration files."""

    configured_status: ConfiguredStatus
    alias: list[str]
    alias_archived: list[str]

    def __str__(self) -> str:
        """Generate a display string for the response.

        Returns:
            str: f"Archived but not in config."
        """
        display = (
            "Archived but not in config."
            if self.configured_status == ConfiguredStatus.Archived
            else "Configured but not in archiver."
        )
        if self.alias:
            display = f"{display} Has aliases {self.alias}."
        if self.alias_archived:
            display = f"{display} Has aliases {self.alias_archived} archived."
        return display

    def __hash__(self) -> int:
        """Hash method for NoConfigResponse.

        Returns:
            int: returns the has of the string representation.
        """
        return hash(str(self))


@dataclass(frozen=True)
class Ioc:
    """Minimal info on an Ioc."""

    hostname: str
    name: str

    @classmethod
    def from_channel(cls, channel: Channel) -> "Ioc":
        """Gets IOC info from a channel."""
        return Ioc(channel.properties["hostName"], channel.properties["iocName"])


UNKNOWN_IOC: Ioc = Ioc("unknown.ioc", "UNKNOWN:IOC")
