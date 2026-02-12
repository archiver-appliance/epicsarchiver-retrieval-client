import datetime
import json
from urllib.parse import quote

import pandas as pd
import pytest
import responses
from pytz import UTC
from responses import matchers

from epicsarchiver.retrieval.archive_event import ArchiveEvent, year_timestamp
from epicsarchiver.retrieval.archiver_retrieval.archiver_retrieval import (
    ArchiverRetrieval,
)
from epicsarchiver.retrieval.EPICSEvent_pb2 import (
    SCALAR_DOUBLE,
    SCALAR_INT,
    PayloadInfo,
)
from epicsarchiver.retrieval.pb import to_field_value
from tests.retrieval.fake_data import TEST_EVENTS, TEST_EVENTS_2, create_pb_bytes


@responses.activate
def test_get_data() -> None:
    host = "archiver.example.org"
    pv = "mypv"
    events = TEST_EVENTS
    dates = [
        pd.Timestamp(
            (year_timestamp(2018) + d.secondsintoyear) * int(1e9) + d.nano,
            tz=UTC,
        )
        for d in events
    ]
    pd_dates = pd.DatetimeIndex(
        dates,
        tz=UTC,
    )
    ref_df = pd.DataFrame([e.val for e in TEST_EVENTS], index=pd_dates)
    ref_df = ref_df.rename_axis("date")
    ref_df.columns = pd.Index(["val"], dtype="str")
    responses.add(
        responses.GET,
        f"http://{host}:17665/mgmt/bpl/getApplianceInfo",
        json={"dataRetrievalURL": "http://archiver-01:17668/retrieval"},
        status=200,
    )
    responses.add(
        responses.GET,
        "http://archiver-01:17668/retrieval/data/getData.raw",
        body=create_pb_bytes(
            events,
            PayloadInfo(type=SCALAR_INT, pvname=pv, year=2018),
        ),
        status=200,
        match=[
            matchers.query_string_matcher(
                f"pv={pv}&from=2018-08-25T17%3A45%3A00.000000Z&"
                "to=2018-08-25T18%3A45%3A00.000000Z"
            )
        ],
    )
    archiver = ArchiverRetrieval(host)
    resp_data = archiver.get_data(pv, "20180825 17:45", "20180825 18:45")
    assert len(responses.calls) == 2
    pd.testing.assert_frame_equal(ref_df, resp_data)


@responses.activate
def test_search_with_no_time_range() -> None:
    host = "archiver.example.org"
    query = "m?l-0[6-7]0RFC:*:*ambi[a-e]nt*"
    regex = "(?i)^" + query.replace("*", ".*").replace("?", ".") + "$"
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
    responses.add(
        responses.GET,
        f"http://{host}:17665/mgmt/bpl/getApplianceInfo",
        json={"dataRetrievalURL": "http://archiver-01:17668/retrieval"},
        status=200,
    )
    responses.add(
        responses.GET,
        "http://archiver-01:17668/retrieval/bpl/getMatchingPVs",
        body=json.dumps(ref_pv_list),
        status=200,
        match=[matchers.query_string_matcher(f"regex={quote(regex)}&limit=500")],
    )

    archiver = ArchiverRetrieval(host)
    resp_data = archiver.search(
        query=query,
        start=None,
        end=None,
        limit=500,
    )
    assert len(responses.calls) == 2
    assert resp_data == ref_pv_list


@responses.activate
def test_search_with_time_range() -> None:
    host = "archiver.example.org"
    query = "m?l-0[6-7]0RFC:*:*ambi[a-e]nt*"
    regex = "(?i)^" + query.replace("*", ".*").replace("?", ".") + "$"
    start = datetime.datetime(2026, 1, 6, 2, 49, 0, tzinfo=UTC)
    end = datetime.datetime(2026, 1, 6, 2, 50, 0, tzinfo=UTC)
    events = TEST_EVENTS_2

    # The intial query for pv names returns a list of pvs
    ref_pv_list_initial = [
        "MBL-060RFC:RFS-CCU-120:TempAmbient",
        "MBL-060RFC:RFS-CCU-220:TempAmbient",
        "MBL-060RFC:RFS-CCU-320:TempAmbient",
        "MBL-060RFC:RFS-CCU-420:TempAmbient",
        "MBL-070RFC:RFS-CCU-120:TempAmbient",
        "MBL-070RFC:RFS-CCU-220:TempAmbient",
        "MBL-070RFC:RFS-CCU-320:TempAmbient",
        "MBL-070RFC:RFS-CCU-420:TempAmbient",
    ]
    # Subsequent data queries will have timestamps that will be checked to see if
    # they are in given range, only one event qualifies
    ref_pv_list_final = ["MBL-070RFC:RFS-CCU-420:TempAmbient"]

    responses.add(
        responses.GET,
        f"http://{host}:17665/mgmt/bpl/getApplianceInfo",
        json={"dataRetrievalURL": "http://archiver-01:17668/retrieval"},
        status=200,
    )
    responses.add(
        responses.GET,
        "http://archiver-01:17668/retrieval/bpl/getMatchingPVs",
        body=json.dumps(ref_pv_list_initial),
        status=200,
        match=[matchers.query_string_matcher(f"regex={quote(regex)}&limit=500")],
    )

    for pv, event in zip(ref_pv_list_initial, events):
        responses.add(
            responses.GET,
            "http://archiver-01:17668/retrieval/data/getData.raw",
            body=create_pb_bytes(
                [event],
                PayloadInfo(type=SCALAR_DOUBLE, pvname=pv, year=2026),
            ),
            status=200,
            match=[
                matchers.query_string_matcher(
                    f"pv={quote(pv)}&from=2026-01-06T02%3A50%3A00.000000Z&"
                    "to=2026-01-06T02%3A50%3A00.000000Z"
                )
            ],
        )

    archiver = ArchiverRetrieval(host)
    resp_data = archiver.search(
        query=query,
        start=start,
        end=end,
        limit=500,
    )
    assert len(responses.calls) == 10
    assert resp_data == ref_pv_list_final


@responses.activate
def test_get_events_pb() -> None:
    host = "archiver.example.org"
    pv = "mypv"
    events = TEST_EVENTS
    responses.add(
        responses.GET,
        f"http://{host}:17665/mgmt/bpl/getApplianceInfo",
        json={"dataRetrievalURL": "http://archiver-01:17668/retrieval"},
        status=200,
    )
    responses.add(
        responses.GET,
        "http://archiver-01:17668/retrieval/data/getData.raw",
        body=create_pb_bytes(
            events,
            PayloadInfo(type=SCALAR_INT, pvname=pv, year=2018),
        ),
        status=200,
        match=[
            matchers.query_string_matcher(
                f"pv={pv}&from=2018-08-25T17%3A45%3A00.000000Z&"
                "to=2018-08-25T18%3A45%3A00.000000Z"
            )
        ],
    )
    archiver = ArchiverRetrieval(host)
    res_data = archiver.get_events(
        pv,
        datetime.datetime(2018, 8, 25, 17, 45, tzinfo=UTC),
        datetime.datetime(2018, 8, 25, 18, 45, tzinfo=UTC),
    )
    assert len(responses.calls) == 2
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


# Test ArchiverRetrieval


@responses.activate
@pytest.mark.parametrize("host", ["archiver-01.example.com", "192.168.4.75"])
def test_data_url_with_same_archiver_host(host: str) -> None:
    data = {"dataRetrievalURL": "http://archiver-01:17668/retrieval"}
    responses.add(
        responses.GET,
        f"http://{host}:17665/mgmt/bpl/getApplianceInfo",
        json=data,
        status=200,
    )
    archiver = ArchiverRetrieval(host)
    data_url = archiver.data_url
    assert len(responses.calls) == 1
    assert data_url == "http://archiver-01:17668/retrieval/data/getData.raw"
    # data_url shall be cached
    _ = archiver.data_url
    assert len(responses.calls) == 1


@responses.activate
def test_data_url_with_no_specific_port() -> None:
    data = {"dataRetrievalURL": "http://archiver-01/foo"}
    responses.add(
        responses.GET,
        "http://archiver-01.example.com:17665/mgmt/bpl/getApplianceInfo",
        json=data,
        status=200,
    )
    archiver = ArchiverRetrieval("archiver-01.example.com")
    data_url = archiver.data_url
    assert len(responses.calls) == 1
    assert data_url == "http://archiver-01/foo/data/getData.raw"
