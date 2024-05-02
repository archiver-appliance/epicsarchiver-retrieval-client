"""Handles the PVDetails report per PV from the Archiver."""

from __future__ import annotations

from enum import Enum
from typing import Dict

from epicsarchiver.statistics.report import Stat
from epicsarchiver.statistics.stat_responses import (
    BaseStatResponse,
    ConnectionStatus,
    DisconnectedPVsResponse,
    DroppedPVResponse,
    DroppedReason,
    LostConnectionsResponse,
    SilentPVsResponse,
    StorageRatesResponse,
    parse_archiver_datetime,
)


class DetailEnum(str, Enum):
    """Enum of detail types present in the archiver per PV."""

    PVName = "PV Name"
    DBRType = "Archiver DBR type (from typeinfo):"
    PVAccess = "Are we using PVAccess?"
    Method = "Sampling method:"
    Period = "Sampling period:"
    Capacity = "Sample buffer capacity"
    EventRate = "Estimated event rate (events/sec)"
    EventsLost = "How many events lost totally so far?"
    TotalEvents = "How many events so far?"
    Connnected = "Is this PV currently connected?"
    LastLostConnection = "When did we last lose a connection to this PV?"
    LostConnections = (
        "How many times have we lost and regained the connection to this PV?"
    )
    LostEventsTimestamp = (
        "How many events lost because the timestamp is "
        "in the far future or past so far?"
    )
    LostEventsBuffer = "How many events lost because the sample buffer is full so far?"
    LostEventsType = (
        "How many events lost because the DBR_Type of the PV "
        "has changed from what it used to be?"
    )
    MBStorageRate = "Estimated storage rate (MB/day)"
    LastEvent = "When did we receive the last event?"
    Hostname = "Hostname of PV from CA"
    Instance = "Instance archiving PV"
    CommandThread = "The CAJ command thread id"

    @classmethod
    def from_str(cls, desc: str) -> DetailEnum | None:
        """Convert from a string to DetailEnum.

        Args:
            desc (str): input string

        Returns:
            DetailEnum | None: An enum representation.
        """
        for e in DetailEnum:
            if e.value == desc:
                return e
        return None


class Details(Dict[DetailEnum, str]):
    """Representation of the response from the pvDetails endpoint in archiver."""

    @classmethod
    def from_json(cls, json: list[dict[str, str]]) -> Details:
        """Convert from the json representation at the Archiver Endpoint.

        Takes some of the details which are relevant for reports to create Details.

        Args:
            json (list[dict[str, str]]): input json

        Returns:
            Details: dictionary of DetailEnum to string value.
        """
        result: Details = Details()
        for json_det in json:
            detail_enum = DetailEnum.from_str(json_det["name"])
            if detail_enum:
                result[detail_enum] = json_det["value"]
        return result

    def to_base_responses(self) -> dict[Stat, BaseStatResponse]:
        """Convert to a BaseStatResponse dict to match Generic Archiver Statistics.

        Returns:
            dict[Stat, BaseStatResponse]: Stat to BaseStatResponse output
        """
        result: dict[Stat, BaseStatResponse] = {}
        for detail_enum, value in self.items():
            response = self.detail_to_base_response(detail_enum, value)
            if response:
                result[response[0]] = response[1]
        return result

    def detail_to_base_response(  # noqa: PLR0911
        self, detail_enum: DetailEnum, value: str
    ) -> tuple[Stat, BaseStatResponse] | None:
        """Convert a single detail to a Stat and BaseStatResponse.

        Args:
            pv_name (str): Name of pv detail is about.
            detail_enum (DetailEnum): Detail
            value (str): String value of the detail

        Returns:
            tuple[Stat, BaseStatResponse] | None: Output
        """
        pv_name = self[DetailEnum.PVName]
        if detail_enum == DetailEnum.LostEventsTimestamp:
            return (
                Stat.IncorrectTimestamp,
                DroppedPVResponse(
                    pv_name, int(value), DroppedReason.IncorrectTimestamp
                ),
            )

        if detail_enum == DetailEnum.LostEventsType:
            return (
                Stat.TypeChange,
                DroppedPVResponse(pv_name, int(value), DroppedReason.TypeChange),
            )

        if detail_enum == DetailEnum.LostEventsBuffer:
            return (
                Stat.BufferOverflow,
                DroppedPVResponse(pv_name, int(value), DroppedReason.BufferOverflow),
            )

        if detail_enum == DetailEnum.Connnected and value != "yes":
            return (
                Stat.DisconnectedPVs,
                DisconnectedPVsResponse(
                    pv_name,
                    self[DetailEnum.Hostname],
                    parse_archiver_datetime(self[DetailEnum.LastLostConnection]),
                    self[DetailEnum.Instance],
                    int(self[DetailEnum.CommandThread]),
                    0,
                    parse_archiver_datetime(self[DetailEnum.LastEvent]),
                ),
            )

        if detail_enum == DetailEnum.LastEvent and value == "Never":
            return (
                Stat.SilentPVs,
                SilentPVsResponse(pv_name, self[DetailEnum.Instance], None),
            )

        if detail_enum == DetailEnum.LostConnections:
            return (
                Stat.LostConnection,
                LostConnectionsResponse(
                    pv_name,
                    ConnectionStatus.CurrentlyConnected
                    if self[DetailEnum.Connnected] == "yes"
                    else ConnectionStatus.NotCurrentlyConnected,
                    self[DetailEnum.Instance],
                    int(value),
                ),
            )

        if detail_enum == DetailEnum.MBStorageRate:
            return (
                Stat.StorageRates,
                StorageRatesResponse(pv_name, float(value), None, None),
            )
        return None
