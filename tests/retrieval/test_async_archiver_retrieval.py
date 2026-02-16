import datetime
import json
import logging
from urllib.parse import quote

import pytest
from aioresponses import aioresponses
from pytz import UTC
from rich.logging import RichHandler

from epicsarchiver.retrieval.archive_event import ArchiveEvent
from epicsarchiver.retrieval.archiver_retrieval.async_archiver_retrieval import (
    AsyncArchiverRetrieval,
)
from epicsarchiver.retrieval.EPICSEvent_pb2 import (
    SCALAR_DOUBLE,
    SCALAR_INT,
    PayloadInfo,
)
from epicsarchiver.retrieval.pb import to_field_value
from tests.retrieval.fake_data import TEST_EVENTS, TEST_EVENTS_2, create_pb_bytes

logging.basicConfig(
    level=logging.DEBUG,
    handlers=[RichHandler(rich_tracebacks=True)],
)
LOG: logging.Logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_get_events_pb() -> None:
    with aioresponses() as mocked:
        host = "archiver.example.org"
        pv = "mypv"
        events = TEST_EVENTS
        app_info_url = f"http://{host}:17665/mgmt/bpl/getApplianceInfo"

        mocked.get(
            app_info_url,
            body=json.dumps({"dataRetrievalURL": "http://archiver-01:17668/retrieval"}),
        )
        data_request_url = f"http://archiver-01:17668/retrieval/data/getData.raw?pv={pv}&from=2018-08-25T17%3A45%3A00.000000Z&to=2018-08-25T18%3A45%3A00.000000Z&fetchLatestMetadata=true"
        mocked.get(
            data_request_url,
            body=create_pb_bytes(
                events,
                PayloadInfo(type=SCALAR_INT, pvname=pv, year=2018),
            ),
        )
        async with AsyncArchiverRetrieval(host) as archiver:
            res_data = await archiver.get_events(
                pv,
                datetime.datetime(2018, 8, 25, 17, 45, tzinfo=UTC),
                datetime.datetime(2018, 8, 25, 18, 45, tzinfo=UTC),
            )
            mocked.assert_any_call(app_info_url)
            mocked.assert_any_call(data_request_url)

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
    with aioresponses() as mocked:
        host = "archiver.example.org"
        query = "qu[h-j]ck:*:fox-[1-8]"
        regex = "(?i)^" + query.replace("*", ".*").replace("?", ".") + "$"
        app_info_url = f"http://{host}:17665/mgmt/bpl/getApplianceInfo"

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

        mocked.get(
            app_info_url,
            body=json.dumps({"dataRetrievalURL": "http://archiver-01:17668/retrieval"}),
        )
        data_request_url = f"http://archiver-01:17668/retrieval/bpl/getMatchingPVs?regex={quote(regex)}&limit=500"
        mocked.get(
            data_request_url,
            body=json.dumps(ref_pv_list),
        )
        async with AsyncArchiverRetrieval(host) as archiver:
            resp_data = await archiver.search(
                query=query,
                start=None,
                end=None,
                limit=500,
            )
            mocked.assert_any_call(app_info_url)
            mocked.assert_any_call(data_request_url)

            assert resp_data == ref_pv_list


@pytest.mark.asyncio
async def test_search_with_time_range() -> None:
    with aioresponses() as mocked:
        host = "archiver.example.org"
        query = "qu[h-j]ck:*:fox-[1-8]"
        regex = "(?i)^" + query.replace("*", ".*").replace("?", ".") + "$"
        app_info_url = f"http://{host}:17665/mgmt/bpl/getApplianceInfo"
        start = datetime.datetime(2026, 1, 6, 2, 49, 0, tzinfo=UTC)
        end = datetime.datetime(2026, 1, 6, 2, 50, 0, tzinfo=UTC)
        events = TEST_EVENTS_2

        # The intial query for pv names returns a list of pvs
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
        # Subsequent data queries will have timestamps that will be checked to see if
        # they are in given range, only one event qualifies
        ref_pv_list_final = ["Quick:Brown:Fox-8"]

        mocked.get(
            app_info_url,
            body=json.dumps({"dataRetrievalURL": "http://archiver-01:17668/retrieval"}),
        )

        matching_pvs_url = (
            "http://archiver-01:17668/retrieval/bpl/getMatchingPVs?"
            f"regex={quote(regex)}&limit=500"
        )
        mocked.get(
            matching_pvs_url,
            body=json.dumps(ref_pv_list_initial),
        )

        data_request_url = (
            "http://archiver-01:17668/retrieval/data/getData.raw?"
            "pv={pv}&from=2026-01-06T02%3A50%3A00.000000Z&"
            "to=2026-01-06T02%3A50%3A00.000000Z&fetchLatestMetadata=true"
        )
        for pv, event in zip(ref_pv_list_initial, events):
            mocked.get(
                data_request_url.format(pv=quote(pv)),
                body=create_pb_bytes(
                    [event],
                    PayloadInfo(type=SCALAR_DOUBLE, pvname=pv, year=2026),
                ),
            )

        async with AsyncArchiverRetrieval(host) as archiver:
            resp_data = await archiver.search(
                query=query,
                start=start,
                end=end,
                limit=500,
            )
            mocked.assert_any_call(app_info_url)
            mocked.assert_any_call(matching_pvs_url)

            for pv in ref_pv_list_initial:
                mocked.assert_any_call(data_request_url.format(pv=quote(pv)))

            assert resp_data == ref_pv_list_final


@pytest.mark.asyncio
async def test_get_all_events_pb() -> None:
    with aioresponses() as mocked:
        host = "archiver.example.org"
        pvs = {"mypv1", "mypv2"}
        events = TEST_EVENTS
        app_info_url = f"http://{host}:17665/mgmt/bpl/getApplianceInfo"

        mocked.get(
            app_info_url,
            body=json.dumps({"dataRetrievalURL": "http://archiver-01:17668/retrieval"}),
        )
        data_request_url = "http://archiver-01:17668/retrieval/data/getData.raw?pv={pv}&from=2018-08-25T17%3A45%3A00.000000Z&to=2018-08-25T18%3A45%3A00.000000Z&fetchLatestMetadata=true"
        for pv in pvs:
            mocked.get(
                data_request_url.format(pv=pv),
                body=create_pb_bytes(
                    events,
                    PayloadInfo(type=SCALAR_INT, pvname=pv, year=2018),
                ),
            )

        async with AsyncArchiverRetrieval(host) as archiver:
            res_data = await archiver.get_all_events(
                pvs,
                datetime.datetime(2018, 8, 25, 17, 45, tzinfo=UTC),
                datetime.datetime(2018, 8, 25, 18, 45, tzinfo=UTC),
            )
            mocked.assert_any_call(app_info_url)
            for pv in pvs:
                mocked.assert_any_call(data_request_url.format(pv=pv))

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
