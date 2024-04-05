"""Tests for `epicsarchiver.statistics` package."""

import datetime
from pathlib import Path

import pytest
import pytz
import responses
from pytest_mock import MockFixture

from epicsarchiver.channelfinder import Channel, ChannelFinder
from epicsarchiver.epicsarchiver import ArchiverAppliance, ArchiverStatistics
from epicsarchiver.statistics._external_stats import (
    get_double_archived,
    get_not_configured,
)
from epicsarchiver.statistics.stat_responses import (
    BothArchiversResponse,
    ConfiguredStatus,
    ConnectionStatus,
    DisconnectedPVsResponse,
    DroppedPVResponse,
    DroppedReason,
    LostConnectionsResponse,
    NoConfigResponse,
    PausedPVResponse,
    SilentPVsResponse,
    StorageRatesResponse,
    _parse_archiver_datetime,
)

SAMPLES_PATH = Path(__file__).parent.resolve() / "samples"


# Test ArchiverStatistics


@responses.activate
def test_get_pvs_dropped() -> None:
    archiver = ArchiverStatistics("archiver.example.org")
    reason = DroppedReason.BufferOverflow
    responses.add(
        responses.GET,
        f"http://archiver.example.org:17665/mgmt/bpl/getPVsByDroppedEventsBuffer?limit={1000}",
        json=[{"eventsDropped": "30", "pvName": "MY:PV"}],
        status=200,
        match_querystring=True,
    )
    pvs_dropped = archiver.get_pvs_dropped(reason)
    assert len(responses.calls) == 1
    assert [DroppedPVResponse("MY:PV", 30, reason)] == pvs_dropped


@responses.activate
def test_get_disconnected_pvs() -> None:
    archiver = ArchiverStatistics("archiver.example.org")
    responses.add(
        responses.GET,
        "http://archiver.example.org:17665/mgmt/bpl/getCurrentlyDisconnectedPVs",
        json=[
            {
                "hostName": "N/A",
                "connectionLostAt": "Sep/14/2023 16:00:18 +02:00",
                "pvName": "MY:PV",
                "instance": "archiver.example.org",
                "commandThreadID": "6",
                "noConnectionAsOfEpochSecs": "1694700018",
                "lastKnownEvent": "Aug/25/2023 15:38:17 +02:00",
            }
        ],
        status=200,
        match_querystring=True,
    )
    pvs_disconnected = archiver.get_disconnected_pvs()
    assert len(responses.calls) == 1
    assert [
        DisconnectedPVsResponse(
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
        )
    ] == pvs_disconnected


@responses.activate
def test_get_silent_pvs() -> None:
    archiver = ArchiverStatistics("archiver.example.org")
    responses.add(
        responses.GET,
        "http://archiver.example.org:17665/mgmt/bpl/getSilentPVsReport?limit=1000",
        json=[
            {
                "pvName": "MY:PV",
                "instance": "archiver.example.org",
                "lastKnownEvent": "Aug/25/2023 15:38:17 +02:00",
            }
        ],
        status=200,
        match_querystring=True,
    )
    pvs_response = archiver.get_silent_pvs()
    assert len(responses.calls) == 1
    assert [
        SilentPVsResponse(
            "MY:PV",
            "archiver.example.org",
            datetime.datetime.fromisoformat("2023-08-25T15:38:17+02:00").replace(
                tzinfo=pytz.utc
            ),
        )
    ] == pvs_response


@responses.activate
def test_get_lost_connections_pvs() -> None:
    archiver = ArchiverStatistics("archiver.example.org")
    responses.add(
        responses.GET,
        "http://archiver.example.org:17665/mgmt/bpl/getLostConnectionsReport?limit=1000",
        json=[
            {
                "currentlyConnected": "Yes",
                "pvName": "MY:PV",
                "instance": "archiver.example.org",
                "lostConnections": "2586",
            }
        ],
        status=200,
        match_querystring=True,
    )
    pvs_response = archiver.get_lost_connections_pvs()
    assert len(responses.calls) == 1
    assert [
        LostConnectionsResponse(
            "MY:PV",
            ConnectionStatus.CurrentlyConnected,
            "archiver.example.org",
            2586,
        )
    ] == pvs_response


@responses.activate
def test_get_paused_pvs() -> None:
    archiver = ArchiverStatistics("archiver.example.org")
    responses.add(
        responses.GET,
        "http://archiver.example.org:17665/mgmt/bpl/getPausedPVsReport",
        json=[
            {
                "pvName": "MY:PV",
                "instance": "archiver",
                "modificationTime": "Sep/12/2023 16:38:56 +02:00",
            }
        ],
        status=200,
        match_querystring=True,
    )
    pvs_response = archiver.get_paused_pvs()
    assert len(responses.calls) == 1
    assert [
        PausedPVResponse("MY:PV", "archiver", "Sep/12/2023 16:38:56 +02:00")
    ] == pvs_response


@responses.activate
def test_get_storage_rates() -> None:
    archiver = ArchiverStatistics("archiver.example.org")
    responses.add(
        responses.GET,
        "http://archiver.example.org:17665/mgmt/bpl/getStorageRateReport?limit=1000",
        json=[
            {
                "pvName": "MY:PV",
                "storageRate_MBperDay": "1099.2894956029622",
                "storageRate_KBperHour": "46903.01847905972",
                "storageRate_GBperYear": "391.8365877881653",
            }
        ],
        status=200,
        match_querystring=True,
    )
    pvs_response = archiver.get_storage_rates()
    assert len(responses.calls) == 1
    assert [
        StorageRatesResponse(
            "MY:PV", 1099.2894956029622, 46903.01847905972, 391.8365877881653
        )
    ] == pvs_response


@responses.activate
@pytest.mark.asyncio
async def test_get_double_archived() -> None:
    archiver = ArchiverAppliance("archiver.example.org")
    other_archiver = ArchiverAppliance("other_archiver.example.org")
    responses.add(
        responses.GET,
        "http://archiver.example.org:17665/mgmt/bpl/getAllPVs?limit=-1",
        json=["MY:PV", "MY:PV2"],
        status=200,
        match_querystring=True,
    )
    responses.add(
        responses.GET,
        "http://archiver.example.org:17665/mgmt/bpl/getPausedPVsReport",
        json=[],
        status=200,
        match_querystring=True,
    )
    responses.add(
        responses.GET,
        "http://other_archiver.example.org:17665/mgmt/bpl/getAllPVs?limit=-1",
        json=["MY:PV", "MY:PV3"],
        status=200,
        match_querystring=True,
    )
    responses.add(
        responses.GET,
        "http://other_archiver.example.org:17665/mgmt/bpl/getPausedPVsReport",
        json=[],
        status=200,
        match_querystring=True,
    )
    pvs_response = await get_double_archived(archiver, other_archiver)
    assert len(responses.calls) == 4
    assert [
        BothArchiversResponse("MY:PV", archiver.hostname, other_archiver.hostname)
    ] == pvs_response


@responses.activate
@pytest.mark.asyncio
async def test_get_not_configured(mocker: MockFixture) -> None:
    archiver = ArchiverAppliance("archiver.example.org")
    channelfinder = ChannelFinder("channelfinder.example.org")
    config_gitlab_repo = Path()
    responses.add(
        responses.GET,
        "http://archiver.example.org:17665/mgmt/bpl/getAllPVs?limit=-1",
        json=["MY:PV", "MY:PV2"],
        status=200,
        match_querystring=True,
    )
    responses.add(
        responses.GET,
        "http://archiver.example.org:17665/mgmt/bpl/getPausedPVsReport",
        json=[],
        status=200,
        match_querystring=True,
    )
    # covers both get_all_channels and get_all_alias_channels
    mocker.patch(
        "epicsarchiver.channelfinder._fetch",
        return_value=[Channel("MY:PV", {"alias": "MY:PV3"}, [])],
    )
    mocker.patch(
        "epicsarchiver.gitlab.Gitlab.get_tar_ball",
        return_value=SAMPLES_PATH,
    )
    pvs_response = await get_not_configured(archiver, channelfinder, config_gitlab_repo)
    assert len(responses.calls) == 2
    assert {
        NoConfigResponse("MY:PV", ConfiguredStatus.Archived, [], []),
        NoConfigResponse("MY:PV3", ConfiguredStatus.Configured, ["MY:PV"], ["MY:PV"]),
    } == set(pvs_response)


@pytest.mark.parametrize(
    ("test_input", "expected"),
    [
        (
            "Feb/07/2024 20:55:42 UTC",
            datetime.datetime(
                year=2024,
                month=2,
                day=7,
                hour=20,
                minute=55,
                second=42,
                tzinfo=pytz.utc,
            ),
        ),
        (
            "Feb/07/2024 20:55:42 Z",
            datetime.datetime(
                year=2024,
                month=2,
                day=7,
                hour=20,
                minute=55,
                second=42,
                tzinfo=pytz.utc,
            ),
        ),
        ("Never", None),
        ("", None),
    ],
)
def test_parse_archiver_datetime(test_input: str, expected: datetime.datetime) -> None:
    assert _parse_archiver_datetime(test_input) == expected
