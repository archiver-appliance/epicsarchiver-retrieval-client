"""Tests for `epicsarchiver.statistics.stat_responses` package."""

import datetime
import json
from pathlib import Path

import pytest
import pytz
import responses
from aioresponses import aioresponses

from epicsarchiver.statistics._external_stats import (
    get_double_archived,
)
from epicsarchiver.statistics.models.stat_responses import (
    BothArchiversResponse,
    ConnectionStatus,
    DisconnectedPVsResponse,
    DroppedPVResponse,
    DroppedReason,
    LostConnectionsResponse,
    PausedPVResponse,
    SilentPVsResponse,
    StorageRatesResponse,
    parse_archiver_datetime,
)
from epicsarchiver.statistics.services.archiver_statistics import (
    ArchiverStatistics,
    ArchiverWrapper,
)

SAMPLES_PATH = Path(__file__).parent.resolve() / "samples"


# Test ArchiverStatistics


@pytest.mark.asyncio
async def test_get_pvs_dropped() -> None:
    with aioresponses() as mocked:
        url = "http://archiver.example.org:17665/mgmt/bpl/getPVsByDroppedEventsBuffer?limit=1000"
        archiver = ArchiverStatistics("archiver.example.org")
        reason = DroppedReason.BufferOverflow
        mocked.get(
            url,
            body=json.dumps([{"eventsDropped": "30", "pvName": "MY:PV"}]),
        )
        pvs_dropped = await archiver.get_pvs_dropped(reason)
        mocked.assert_any_call(url)
        assert [DroppedPVResponse("MY:PV", 30, reason)] == pvs_dropped
        await archiver.close()


@pytest.mark.asyncio
async def test_get_disconnected_pvs() -> None:
    with aioresponses() as mocked:
        url = "http://archiver.example.org:17665/mgmt/bpl/getCurrentlyDisconnectedPVs"
        archiver = ArchiverStatistics("archiver.example.org")
        mocked.get(
            url,
            body=json.dumps([
                {
                    "hostName": "N/A",
                    "connectionLostAt": "Sep/14/2023 16:00:18 +02:00",
                    "pvName": "MY:PV",
                    "instance": "archiver.example.org",
                    "commandThreadID": "6",
                    "noConnectionAsOfEpochSecs": "1694700018",
                    "lastKnownEvent": "Aug/25/2023 15:38:17 +02:00",
                },
            ]),
        )
        pvs_disconnected = await archiver.get_disconnected_pvs()
        mocked.assert_any_call(url)
        assert [
            DisconnectedPVsResponse(
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
        ] == pvs_disconnected
        await archiver.close()


@pytest.mark.asyncio
async def test_get_silent_pvs() -> None:
    with aioresponses() as mocked:
        url = "http://archiver.example.org:17665/mgmt/bpl/getSilentPVsReport?limit=1000"
        archiver = ArchiverStatistics("archiver.example.org")
        mocked.get(
            url,
            body=json.dumps([
                {
                    "pvName": "MY:PV",
                    "instance": "archiver.example.org",
                    "lastKnownEvent": "Aug/25/2023 15:38:17 +02:00",
                },
            ]),
        )
        pvs_response = await archiver.get_silent_pvs()
        mocked.assert_any_call(url)
        assert [
            SilentPVsResponse(
                "MY:PV",
                "archiver.example.org",
                datetime.datetime.fromisoformat("2023-08-25T15:38:17+02:00").replace(
                    tzinfo=pytz.utc,
                ),
            ),
        ] == pvs_response
        await archiver.close()


@pytest.mark.asyncio
async def test_get_lost_connections_pvs() -> None:
    with aioresponses() as mocked:
        archiver = ArchiverStatistics("archiver.example.org")
        url = "http://archiver.example.org:17665/mgmt/bpl/getLostConnectionsReport?limit=1000"
        mocked.get(
            url,
            body=json.dumps([
                {
                    "currentlyConnected": "Yes",
                    "pvName": "MY:PV",
                    "instance": "archiver.example.org",
                    "lostConnections": "2586",
                },
            ]),
        )
        pvs_response = await archiver.get_lost_connections_pvs()
        mocked.assert_any_call(url)
        assert [
            LostConnectionsResponse(
                "MY:PV",
                ConnectionStatus.CurrentlyConnected,
                "archiver.example.org",
                2586,
            ),
        ] == pvs_response
        await archiver.close()


@pytest.mark.asyncio
async def test_get_paused_pvs() -> None:
    with aioresponses() as mocked:
        url = "http://archiver.example.org:17665/mgmt/bpl/getPausedPVsReport"
        archiver = ArchiverStatistics("archiver.example.org")
        mocked.get(
            url,
            body=json.dumps([
                {
                    "pvName": "MY:PV",
                    "instance": "archiver",
                    "modificationTime": "Sep/12/2023 16:38:56 +02:00",
                },
            ]),
        )
        pvs_response = await archiver.get_paused_pvs()
        mocked.assert_any_call(url)
        assert [
            PausedPVResponse("MY:PV", "archiver", "Sep/12/2023 16:38:56 +02:00"),
        ] == pvs_response
        await archiver.close()


@pytest.mark.asyncio
async def test_get_storage_rates() -> None:
    with aioresponses() as mocked:
        archiver = ArchiverStatistics("archiver.example.org")
        url = (
            "http://archiver.example.org:17665/mgmt/bpl/getStorageRateReport?limit=1000"
        )
        mocked.get(
            url,
            body=json.dumps([
                {
                    "pvName": "MY:PV",
                    "storageRate_MBperDay": "1099.2894956029622",
                    "storageRate_KBperHour": "46903.01847905972",
                    "storageRate_GBperYear": "391.8365877881653",
                },
            ]),
        )
        pvs_response = await archiver.get_storage_rates()
        mocked.assert_any_call(url)
        assert [
            StorageRatesResponse(
                "MY:PV",
                1099.2894956029622,
                46903.01847905972,
                391.8365877881653,
            ),
        ] == pvs_response
        await archiver.close()


@responses.activate
@pytest.mark.asyncio
async def test_get_double_archived() -> None:
    responses.add(
        responses.GET,
        "http://archiver.example.org:17665/mgmt/bpl/getAllPVs?limit=-1",
        json=["MY:PV", "MY:PV2"],
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
    with aioresponses() as mocked:
        archiver = ArchiverWrapper("archiver.example.org")
        other_archiver = ArchiverWrapper("other_archiver.example.org")
        mocked.get(
            "http://archiver.example.org:17665/mgmt/bpl/getPausedPVsReport",
            body=json.dumps([]),
        )
        mocked.get(
            "http://other_archiver.example.org:17665/mgmt/bpl/getAllPVs?limit=-1",
            body=json.dumps(["MY:PV", "MY:PV3"]),
        )
        mocked.get(
            "http://other_archiver.example.org:17665/mgmt/bpl/getPausedPVsReport",
            body=json.dumps([]),
        )
        pvs_response = await get_double_archived(archiver, other_archiver)
        mocked.assert_any_call(
            "http://archiver.example.org:17665/mgmt/bpl/getPausedPVsReport"
        )
        mocked.assert_any_call(
            "http://other_archiver.example.org:17665/mgmt/bpl/getPausedPVsReport"
        )
        assert len(responses.calls) == 2
        assert [
            BothArchiversResponse(
                "MY:PV", archiver.mgmt.hostname, other_archiver.mgmt.hostname
            ),
        ] == pvs_response
        await archiver.close()
        await other_archiver.close()


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
    assert parse_archiver_datetime(test_input) == expected
