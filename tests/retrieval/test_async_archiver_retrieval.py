import datetime
import logging
from unittest.mock import AsyncMock

import httpx
import pytest
from pytz import UTC
from rich.logging import RichHandler

from epicsarchiver.retrieval.archive_event import ArchiveEvent
from epicsarchiver.retrieval.client.async_archiver_retrieval import (
    AsyncArchiverRetrieval,
)
from epicsarchiver.retrieval.EPICSEvent_pb2 import (
    SCALAR_DOUBLE,
    SCALAR_INT,
    PayloadInfo,
)
from epicsarchiver.retrieval.pb import to_field_value
from tests.retrieval.conftest import make_response_mock
from tests.retrieval.fake_data import TEST_EVENTS, TEST_EVENTS_2, create_pb_bytes

logging.basicConfig(
    level=logging.DEBUG,
    handlers=[RichHandler(rich_tracebacks=True)],
)
LOG: logging.Logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_get_events_pb() -> None:
    host = "archiver.example.org"
    pv = "mypv"
    events = TEST_EVENTS
    start = datetime.datetime(2018, 8, 25, 17, 45, tzinfo=UTC)
    end = datetime.datetime(2018, 8, 25, 18, 45, tzinfo=UTC)

    pb_body = create_pb_bytes(
        events, PayloadInfo(type=SCALAR_INT, pvname=pv, year=2018)
    )

    async with AsyncArchiverRetrieval(host) as archiver:
        archiver._get = AsyncMock(return_value=make_response_mock(pb_body))  # type: ignore[method-assign]
        res_data = await archiver.get_events(pv, start, end)

    archiver._get.assert_called_once()
    assert res_data == [
        ArchiveEvent(
            pv,
            e.val,
            e.secondsintoyear,
            2018,
            e.nano,
            e.severity,
            e.status,
            [to_field_value(f) for f in e.fieldvalues],
        )
        for e in events
    ]


@pytest.mark.asyncio
async def test_search_with_no_time_range() -> None:
    host = "archiver.example.org"
    query = "(?i)^qu[h-j]ck:.*:fox-[1-8]$"

    ref_pv_list = [
        "Quick:Brown:Fox-1",
        "Quick:Brown:Fox-2",
        "Quick:Brown:Fox-3",
        "Quick:Brown:Fox-4",
        "Quick:Brown:Fox-5",
        "Quick:Brown:Fox-6",
        "Quick:Brown:Fox-7",
        "Quick:Brown:Fox-8",
    ]

    async with AsyncArchiverRetrieval(host) as archiver:
        archiver._get_json = AsyncMock(return_value=ref_pv_list)  # type: ignore[method-assign]
        resp_data = await archiver.search(
            query=query,
            start=None,
            end=None,
            limit=500,
        )

    archiver._get_json.assert_called_once()
    assert resp_data == ref_pv_list


@pytest.mark.asyncio
async def test_search_with_time_range() -> None:
    host = "archiver.example.org"
    query = "(?i)^qu[h-j]ck:.*:fox-[1-8]$"
    start = datetime.datetime(2026, 1, 6, 2, 49, 0, tzinfo=UTC)
    end = datetime.datetime(2026, 1, 6, 2, 50, 0, tzinfo=UTC)
    events = TEST_EVENTS_2

    ref_pv_list_initial = [
        "Quick:Brown:Fox-1",
        "Quick:Brown:Fox-2",
        "Quick:Brown:Fox-3",
        "Quick:Brown:Fox-4",
        "Quick:Brown:Fox-5",
        "Quick:Brown:Fox-6",
        "Quick:Brown:Fox-7",
        "Quick:Brown:Fox-8",
    ]
    ref_pv_list_final = ["Quick:Brown:Fox-8"]

    pb_by_pv = {
        pv: create_pb_bytes(
            [event], PayloadInfo(type=SCALAR_DOUBLE, pvname=pv, year=2026)
        )
        for pv, event in zip(ref_pv_list_initial, events, strict=True)
    }

    async with AsyncArchiverRetrieval(host) as archiver:
        archiver._get_json = AsyncMock(return_value=ref_pv_list_initial)  # type: ignore[method-assign]
        archiver._get = AsyncMock(  # type: ignore[method-assign]
            side_effect=lambda _url, params=None: make_response_mock(
                pb_by_pv[params["pv"]]
            )
        )
        resp_data = await archiver.search(
            query=query,
            start=start,
            end=end,
            limit=500,
        )

    archiver._get_json.assert_called_once()
    assert resp_data == ref_pv_list_final


@pytest.mark.asyncio
async def test_get_all_events_pb() -> None:
    host = "archiver.example.org"
    pvs = {"mypv1", "mypv2"}
    events = TEST_EVENTS

    async with AsyncArchiverRetrieval(host) as archiver:
        archiver._get = AsyncMock(  # type: ignore[method-assign]
            side_effect=lambda _url, params=None: make_response_mock(
                create_pb_bytes(
                    events, PayloadInfo(type=SCALAR_INT, pvname=params["pv"], year=2018)
                )
            )
        )
        res_data = await archiver.get_all_events(
            pvs,
            datetime.datetime(2018, 8, 25, 17, 45, tzinfo=UTC),
            datetime.datetime(2018, 8, 25, 18, 45, tzinfo=UTC),
        )

    assert archiver._get.call_count == len(pvs)
    assert res_data == {
        pv: [
            ArchiveEvent(
                pv,
                e.val,
                e.secondsintoyear,
                2018,
                e.nano,
                e.severity,
                e.status,
                [to_field_value(f) for f in e.fieldvalues],
            )
            for e in events
        ]
        for pv in pvs
    }
