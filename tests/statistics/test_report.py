from __future__ import annotations

import datetime
from datetime import timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
import pytz

from epicsarchiver.statistics.archiver_statistics import ArchiverWrapper
from epicsarchiver.statistics.channelfinder import Channel, ChannelFinder
from epicsarchiver.statistics.configuration import ConfigOptions
from epicsarchiver.statistics.report import (
    ArchiverReport,
    PVStats,
    Stat,
    _get_pv_parts,
    _get_pv_parts_stats,
)
from epicsarchiver.statistics.stat_responses import (
    BaseStatResponse,
    BothArchiversResponse,
    ConnectionStatus,
    DisconnectedPVsResponse,
    DroppedPVResponse,
    DroppedReason,
    Ioc,
    LostConnectionsResponse,
    SilentPVsResponse,
    StorageRatesResponse,
)

if TYPE_CHECKING:
    from pytest_mock import MockFixture

expected_all_stats: dict[Stat, BaseStatResponse] = {
    Stat.BufferOverflow: DroppedPVResponse("MY:PV", 11, DroppedReason.BufferOverflow),
    Stat.TypeChange: DroppedPVResponse("MY:PV", 11, DroppedReason.TypeChange),
    Stat.IncorrectTimestamp: DroppedPVResponse(
        "MY:PV",
        11,
        DroppedReason.IncorrectTimestamp,
    ),
    Stat.SlowChanging: DroppedPVResponse("MY:PV", 11, DroppedReason.SlowChanging),
    Stat.DisconnectedPVs: DisconnectedPVsResponse(
        "MY:PV",
        "N/A",
        datetime.datetime.fromisoformat("2023-09-14T16:00:18+02:00").replace(
            tzinfo=pytz.utc,
        ),
        "archiver.example.org",
        6,
        1694700018,
        datetime.datetime.fromisoformat("2023-08-25T15:38:17+02:00").replace(
            tzinfo=pytz.utc,
        ),
    ),
    Stat.SilentPVs: SilentPVsResponse(
        "MY:PV",
        "archiver.example.org",
        datetime.datetime.fromisoformat("2023-08-25T15:38:17+02:00").replace(
            tzinfo=pytz.utc,
        ),
    ),
    Stat.DoubleArchived: BothArchiversResponse(
        "MY:PV",
        "archiver.example.org",
        "other_archiver.example.org",
    ),
    Stat.StorageRates: StorageRatesResponse(
        "MY:PV",
        1,
        2,
        3,
    ),
    Stat.LostConnection: LostConnectionsResponse(
        "MY:PV",
        ConnectionStatus.CurrentlyConnected,
        "archiver.example.org",
        2586,
    ),
}


@pytest.mark.asyncio
async def test_generate_buffer_overflow_stat(mocker: MockFixture) -> None:
    mocker.patch(
        "epicsarchiver.statistics.archiver_statistics.ArchiverStatistics.get_pvs_dropped",
        return_value=[expected_all_stats[Stat.BufferOverflow]],
    )
    archiver = ArchiverWrapper("archiver.example.org")
    report = ArchiverReport(
        query_limit=2,
        time_minimum=timedelta(days=10),
        connection_drops_minimum=10,
        config_options=ConfigOptions(None, None),
        other_archiver=None,
        mb_per_day_minimum=10,
        events_dropped_minimum=1,
        channelfinder=ChannelFinder("channelfinder.example.org"),
        ioc_name=None,
    )
    actual = await report.generate_stats(Stat.BufferOverflow, archiver)
    assert actual == {
        expected_all_stats[Stat.BufferOverflow].pv_name: expected_all_stats[
            Stat.BufferOverflow
        ],
    }


def mock_get_pvs_dropped(
    reason: DroppedReason,
    limit: int,  # noqa: ARG001
) -> list[BaseStatResponse]:
    if reason == DroppedReason.BufferOverflow:
        return [expected_all_stats[Stat.BufferOverflow]]
    if reason == DroppedReason.IncorrectTimestamp:
        return [expected_all_stats[Stat.IncorrectTimestamp]]
    if reason == DroppedReason.TypeChange:
        return [expected_all_stats[Stat.TypeChange]]
    if reason == DroppedReason.SlowChanging:
        return [expected_all_stats[Stat.SlowChanging]]
    return []


@pytest.mark.asyncio
async def test_generate_all_stats(mocker: MockFixture) -> None:
    channel = Channel("MY:PV", {"iocName": "IOCNAME", "hostName": "IOCHOSTNAME"}, [])
    mocker.patch(
        "epicsarchiver.statistics.archiver_statistics.ArchiverStatistics.get_pvs_dropped",
        wraps=mock_get_pvs_dropped,
    )
    mocker.patch(
        "epicsarchiver.statistics.archiver_statistics.ArchiverStatistics.get_disconnected_pvs",
        return_value=[expected_all_stats[Stat.DisconnectedPVs]],
    )
    mocker.patch(
        "epicsarchiver.statistics.archiver_statistics.ArchiverStatistics.get_silent_pvs",
        return_value=[expected_all_stats[Stat.SilentPVs]],
    )
    mocker.patch(
        "epicsarchiver.statistics.archiver_statistics.ArchiverStatistics.get_lost_connections_pvs",
        return_value=[expected_all_stats[Stat.LostConnection]],
    )
    mocker.patch(
        "epicsarchiver.statistics.archiver_statistics.ArchiverStatistics.get_storage_rates",
        return_value=[expected_all_stats[Stat.StorageRates]],
    )
    mocker.patch(
        "epicsarchiver.mgmt.archiver_mgmt.ArchiverMgmt.get_all_pvs",
        return_value=["MY:PV"],
    )
    mocker.patch(
        "epicsarchiver.statistics.archiver_statistics.ArchiverStatistics.get_paused_pvs",
        return_value=[],
    )
    mocker.patch(
        "epicsarchiver.statistics.channelfinder.ChannelFinder.get_channels_chunked",
        side_effect=AsyncMock(return_value={"MY:PV": channel}),
    )
    mocker.patch(
        "epicsarchiver.statistics.channelfinder.ChannelFinder.get_all_alias_channels",
        side_effect=AsyncMock(return_value={"MY:PV": []}),
    )
    archiver = ArchiverWrapper("archiver.example.org")
    other_archiver = ArchiverWrapper("other_archiver.example.org")
    report = ArchiverReport(
        query_limit=2,
        time_minimum=timedelta(days=10),
        connection_drops_minimum=10,
        config_options=None,
        other_archiver=other_archiver,
        mb_per_day_minimum=0,
        events_dropped_minimum=1,
        channelfinder=ChannelFinder("channelfinder.example.org"),
        ioc_name=None,
    )
    ioc = Ioc(channel.properties["hostName"], channel.properties["iocName"])
    actual = await report.generate(archiver)
    assert ioc in actual
    assert "MY:PV" in actual[ioc]
    assert PVStats("MY:PV", expected_all_stats) == actual[ioc]["MY:PV"]


def test_get_pv_parts() -> None:
    assert _get_pv_parts("DTL-030:EMR-SM-003:Axis.URIP") == ["DTL-030", "EMR-SM"]


def test_get_pv_parts_stats() -> None:
    assert _get_pv_parts_stats({
        "DTL-030:EMR-SM-003:Axis.URIP",
        "DTL-030:EMR-SG-003:Axis.URIQ",
        "DTL-030:EMR-SG-002:Axis.URIQ",
    }) == {
        "device": [("EMR-SM", 1), ("EMR-SG", 2)],
        "system": [("DTL-030", 3)],
    }
