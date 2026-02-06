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
from epicsarchiver.retrieval.EPICSEvent_pb2 import SCALAR_INT, PayloadInfo
from epicsarchiver.retrieval.pb import to_field_value
from tests.retrieval.fake_data import TEST_EVENTS, create_pb_bytes

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
        pvstring = "m?l-0[6-7]0RFC:*:*ambi[a-e]nt*"
        regex = "(?i)^" + pvstring.replace("*", ".*").replace("?", ".") + "$"
        app_info_url = f"http://{host}:17665/mgmt/bpl/getApplianceInfo"

        ref_pv_list = [
            "MBL-060RFC:RFS-CCU-120:TempAmbient",
            "MBL-060RFC:RFS-CCU-220:TempAmbient",
            "MBL-060RFC:RFS-CCU-320:TempAmbient",
            "MBL-060RFC:RFS-CCU-420:TempAmbient",
            "MBL-070RFC:RFS-CCU-120:TempAmbient",
            "MBL-070RFC:RFS-CCU-220:TempAmbient",
            "MBL-070RFC:RFS-CCU-320:TempAmbient",
            "MBL-070RFC:RFS-CCU-420:TempAmbient",
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
                pvstrings=pvstring,
                start=None,
                end=None,
                limit=500,
            )
            mocked.assert_any_call(app_info_url)
            mocked.assert_any_call(data_request_url)

            assert resp_data == ref_pv_list


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
