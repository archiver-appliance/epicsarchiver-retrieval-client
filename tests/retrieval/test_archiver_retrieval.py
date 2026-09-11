import datetime

import httpx
import polars as pl
import respx
from polars.testing import assert_frame_equal
from pytz import UTC

from epicsarchiver.common.client import DEFAULT_RETRIEVAL_PORT
from epicsarchiver.common.date_util import NANO_PER_SECOND, year_start_epoch_seconds
from epicsarchiver.retrieval.archive_event import ArchiveEvent
from epicsarchiver.retrieval.client.archiver_retrieval import (
    ArchiverRetrieval,
)
from epicsarchiver.retrieval.EPICSEvent_pb2 import (
    SCALAR_DOUBLE,
    SCALAR_INT,
    PayloadInfo,
)
from epicsarchiver.retrieval.pb import to_field_value
from tests.retrieval.fake_data import TEST_EVENTS, TEST_EVENTS_2, create_pb_bytes


def test_retrieval_urls() -> None:
    archiver = ArchiverRetrieval()
    assert archiver.base_url == f"http://localhost:{DEFAULT_RETRIEVAL_PORT}/retrieval"
    archiver = ArchiverRetrieval("archiver-01.example.com", port=80)
    assert archiver.base_url == "http://archiver-01.example.com:80/retrieval"
    assert (
        archiver.data_url
        == "http://archiver-01.example.com:80/retrieval/data/getData.raw"
    )


@respx.mock
def test_get_data() -> None:
    host = "archiver.example.org"
    pv = "mypv"
    events = TEST_EVENTS
    dates_ns = [
        (year_start_epoch_seconds(2018) + d.secondsintoyear) * NANO_PER_SECOND + d.nano
        for d in events
    ]
    fv_dtype = pl.List(pl.Struct({"name": pl.Utf8, "value": pl.Utf8}))
    ref_df = pl.DataFrame({
        "date": pl.Series(dates_ns, dtype=pl.Datetime("ns", "UTC")),
        "pv": pl.Series([pv for _ in TEST_EVENTS], dtype=pl.Utf8),
        "val": [e.val for e in TEST_EVENTS],
        "severity": pl.Series([e.severity for e in TEST_EVENTS], dtype=pl.Int32),
        "status": pl.Series([e.status for e in TEST_EVENTS], dtype=pl.Int32),
        "field_values": pl.Series(
            [
                [{"name": fv.name, "value": fv.val} for fv in e.fieldvalues]
                for e in TEST_EVENTS
            ],
            dtype=fv_dtype,
        ),
        "headers": pl.Series([[] for _ in TEST_EVENTS], dtype=fv_dtype),
    })
    route = respx.get(
        f"http://{host}:{DEFAULT_RETRIEVAL_PORT}/retrieval/data/getData.raw",
        params={
            "pv": pv,
            "from": "2018-08-25T17:45:00.000000Z",
            "to": "2018-08-25T18:45:00.000000Z",
        },
    ).mock(
        return_value=httpx.Response(
            200,
            content=create_pb_bytes(
                events,
                PayloadInfo(type=SCALAR_INT, pvname=pv, year=2018),
            ),
        )
    )
    archiver = ArchiverRetrieval(host)
    resp_data = archiver.get_data(pv, "20180825 17:45", "20180825 18:45")
    assert route.call_count == 1
    assert_frame_equal(ref_df, resp_data)


@respx.mock
def test_search_with_no_time_range() -> None:
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
    route = respx.get(
        f"http://{host}:{DEFAULT_RETRIEVAL_PORT}/retrieval/bpl/getMatchingPVs",
        params={"regex": query, "limit": "500"},
    ).mock(return_value=httpx.Response(200, json=ref_pv_list))

    archiver = ArchiverRetrieval(host)
    resp_data = archiver.search(
        query=query,
        start=None,
        end=None,
        limit=500,
    )
    assert route.call_count == 1
    assert resp_data == ref_pv_list


@respx.mock
def test_search_with_time_range() -> None:
    host = "archiver.example.org"
    query = "(?i)^qu[h-j]ck:.*:fox-[1-8]$"
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

    search_route = respx.get(
        f"http://{host}:{DEFAULT_RETRIEVAL_PORT}/retrieval/bpl/getMatchingPVs",
        params={"regex": query, "limit": "500"},
    ).mock(return_value=httpx.Response(200, json=ref_pv_list_initial))

    data_routes = [
        respx.get(
            f"http://{host}:17668/retrieval/data/getData.raw",
            params={
                "pv": pv,
                "from": "2026-01-06T02:50:00.000000Z",
                "to": "2026-01-06T02:50:00.000000Z",
            },
        ).mock(
            return_value=httpx.Response(
                200,
                content=create_pb_bytes(
                    [event],
                    PayloadInfo(type=SCALAR_DOUBLE, pvname=pv, year=2026),
                ),
            )
        )
        for pv, event in zip(ref_pv_list_initial, events, strict=True)
    ]

    archiver = ArchiverRetrieval(host)
    resp_data = archiver.search(
        query=query,
        start=start,
        end=end,
        limit=500,
    )
    assert search_route.call_count == 1
    assert all(route.call_count == 1 for route in data_routes)
    assert resp_data == ref_pv_list_final


@respx.mock
def test_get_events_pb() -> None:
    host = "archiver.example.org"
    pv = "mypv"
    events = TEST_EVENTS
    route = respx.get(
        f"http://{host}:{DEFAULT_RETRIEVAL_PORT}/retrieval/data/getData.raw",
        params={
            "pv": pv,
            "from": "2018-08-25T17:45:00.000000Z",
            "to": "2018-08-25T18:45:00.000000Z",
        },
    ).mock(
        return_value=httpx.Response(
            200,
            content=create_pb_bytes(
                events,
                PayloadInfo(type=SCALAR_INT, pvname=pv, year=2018),
            ),
        )
    )
    archiver = ArchiverRetrieval(host)
    _, res_events = archiver.get_events(
        pv,
        datetime.datetime(2018, 8, 25, 17, 45, tzinfo=UTC),
        datetime.datetime(2018, 8, 25, 18, 45, tzinfo=UTC),
    )
    assert route.call_count == 1
    assert res_events == [
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
