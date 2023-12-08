import datetime
from datetime import timedelta
from pathlib import Path

import pytest
import pytz
from pytest_mock import MockFixture

from epicsarchiver.channelfinder import Channel, ChannelFinder
from epicsarchiver.epicsarchiver import ArchiverAppliance
from epicsarchiver.statistics.report import (
    ReportConfig,
    Stat,
    _PVStats,
    generate_all_stats,
)
from epicsarchiver.statistics.stat_responses import (
    BaseStatResponse,
    BothArchiversResponse,
    DisconnectedPVsResponse,
    DroppedPVResponse,
    DroppedReason,
    Ioc,
    LostConnectionsResponse,
    SilentPVsResponse,
    StorageRatesResponse,
)

expected_all_stats: dict[Stat, BaseStatResponse] = {
    Stat.BufferOverflow: DroppedPVResponse("MY:PV", 11, DroppedReason.BufferOverflow),
    Stat.TypeChange: DroppedPVResponse("MY:PV", 11, DroppedReason.TypeChange),
    Stat.IncorrectTimestamp: DroppedPVResponse(
        "MY:PV", 11, DroppedReason.IncorrectTimestamp
    ),
    Stat.SlowChanging: DroppedPVResponse("MY:PV", 11, DroppedReason.SlowChanging),
    Stat.DisconnectedPVs: DisconnectedPVsResponse(
        "MY:PV",
        "N/A",
        datetime.datetime.fromisoformat("2023-09-14T16:00:18+02:00").replace(
            tzinfo=pytz.utc
        ),
        "archiver.example.org",
        6,
        1694700018,
        datetime.datetime.fromisoformat("2023-08-25T15:38:17+02:00").replace(
            tzinfo=pytz.utc
        ),
    ),
    Stat.SilentPVs: SilentPVsResponse(
        "MY:PV",
        "archiver.example.org",
        datetime.datetime.fromisoformat("2023-08-25T15:38:17+02:00").replace(
            tzinfo=pytz.utc
        ),
    ),
    Stat.DoubleArchived: BothArchiversResponse(
        "MY:PV", "archiver.example.org", "other_archiver.example.org"
    ),
    Stat.StorageRates: StorageRatesResponse(
        "MY:PV",
        1,
        2,
        3,
    ),
    Stat.LostConnection: LostConnectionsResponse(
        "MY:PV",
        True,
        "archiver.example.org",
        2586,
    ),
}


@pytest.mark.asyncio
async def test_generate_buffer_overflow_stat(mocker: MockFixture) -> None:
    mocker.patch(
        "epicsarchiver.ArchiverAppliance.get_pvs_dropped",
        return_value=[expected_all_stats[Stat.BufferOverflow]],
    )
    archiver = ArchiverAppliance("archiver.example.org")
    config = ReportConfig(
        query_limit=2,
        time_minimum=timedelta(days=10),
        connection_drops_minimum=10,
        config_files=Path(),
        other_archiver=None,
        mb_per_day_minimum=10,
        events_dropped_minimum=1,
        channelfinder=ChannelFinder("channelfinder.example.org"),
    )
    actual = await Stat.BufferOverflow.generate_stats(archiver, config)
    assert actual == {
        expected_all_stats[Stat.BufferOverflow].pv_name: expected_all_stats[
            Stat.BufferOverflow
        ]
    }


def mock_get_pvs_dropped(
    reason: DroppedReason, limit: int  # noqa: ARG001
) -> list[BaseStatResponse]:
    match reason:
        case DroppedReason.BufferOverflow:
            return [expected_all_stats[Stat.BufferOverflow]]
        case DroppedReason.IncorrectTimestamp:
            return [expected_all_stats[Stat.IncorrectTimestamp]]
        case DroppedReason.TypeChange:
            return [expected_all_stats[Stat.TypeChange]]
        case DroppedReason.SlowChanging:
            return [expected_all_stats[Stat.SlowChanging]]
    return []


@pytest.mark.asyncio
async def test_generate_all_stats(mocker: MockFixture) -> None:
    channel = Channel("MY:PV", {"iocName": "IOCNAME", "hostName": "IOCHOSTNAME"}, [])
    mocker.patch(
        "epicsarchiver.ArchiverAppliance.get_pvs_dropped",
        wraps=mock_get_pvs_dropped,
    )
    mocker.patch(
        "epicsarchiver.ArchiverAppliance.get_disconnected_pvs",
        return_value=[expected_all_stats[Stat.DisconnectedPVs]],
    )
    mocker.patch(
        "epicsarchiver.ArchiverAppliance.get_silent_pvs",
        return_value=[expected_all_stats[Stat.SilentPVs]],
    )
    mocker.patch(
        "epicsarchiver.ArchiverAppliance.get_lost_connections_pvs",
        return_value=[expected_all_stats[Stat.LostConnection]],
    )
    mocker.patch(
        "epicsarchiver.ArchiverAppliance.get_storage_rates",
        return_value=[expected_all_stats[Stat.StorageRates]],
    )
    mocker.patch(
        "epicsarchiver.ArchiverAppliance.get_all_pvs",
        return_value=["MY:PV"],
    )
    mocker.patch(
        "epicsarchiver.ArchiverAppliance.get_paused_pvs",
        return_value=[],
    )
    mocker.patch(
        "epicsarchiver.channelfinder.ChannelFinder.get_all_channels",
        return_value={"MY:PV": channel},
    )
    mocker.patch(
        "epicsarchiver.channelfinder.ChannelFinder.get_all_alias_channels",
        return_value={"MY:PV": []},
    )
    archiver = ArchiverAppliance("archiver.example.org")
    other_archiver = ArchiverAppliance("other_archiver.example.org")
    config = ReportConfig(
        query_limit=2,
        time_minimum=timedelta(days=10),
        connection_drops_minimum=10,
        config_files=Path(),
        other_archiver=other_archiver,
        mb_per_day_minimum=0,
        events_dropped_minimum=1,
        channelfinder=ChannelFinder("channelfinder.example.org"),
    )
    ioc = Ioc(channel.properties["hostName"], channel.properties["iocName"])
    actual = await generate_all_stats(archiver, config)
    assert ioc in actual.keys()
    assert "MY:PV" in actual[ioc].keys()
    assert _PVStats("MY:PV", expected_all_stats) == actual[ioc]["MY:PV"]
