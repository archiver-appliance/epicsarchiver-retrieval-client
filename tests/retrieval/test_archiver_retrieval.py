import pandas as pd
import pytest
import responses
from pytz import UTC

from epicsarchiver.retrieval.archive_event import ArchiveEvent, year_timestamp
from epicsarchiver.retrieval.archiver_retrieval.archiver_retrieval import (
    ArchiverRetrieval,
)
from epicsarchiver.retrieval.EPICSEvent_pb2 import SCALAR_INT, PayloadInfo
from epicsarchiver.retrieval.pb import to_field_value
from tests.retrieval.fake_data import TEST_EVENTS, create_pb_bytes


@responses.activate
def test_get_data() -> None:
    host = "archiver.example.org"
    archiver = ArchiverRetrieval(host)
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
        f"http://archiver-01:17668/retrieval/data/getData.raw?pv={pv}&from=2018-08-25T17%3A45%3A00.000000Z&to=2018-08-25T18%3A45%3A00.000000Z",
        body=create_pb_bytes(
            events,
            PayloadInfo(type=SCALAR_INT, pvname=pv, year=2018),
        ),
        status=200,
        match_querystring=True,
    )
    resp_data = archiver.get_data(pv, "20180825 17:45", "20180825 18:45")
    assert len(responses.calls) == 2
    pd.testing.assert_frame_equal(ref_df, resp_data)


@responses.activate
def test_get_events_pb() -> None:
    host = "archiver.example.org"
    archiver = ArchiverRetrieval(host)
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
        f"http://archiver-01:17668/retrieval/data/getData.raw?pv={pv}&from=2018-08-25T17%3A45%3A00.000000Z&to=2018-08-25T18%3A45%3A00.000000Z",
        body=create_pb_bytes(
            events,
            PayloadInfo(type=SCALAR_INT, pvname=pv, year=2018),
        ),
        status=200,
        match_querystring=True,
    )
    res_data = archiver.get_events(pv, "20180825 17:45", "20180825 18:45")
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
    archiver = ArchiverRetrieval(host)
    data = {"dataRetrievalURL": "http://archiver-01:17668/retrieval"}
    responses.add(
        responses.GET,
        f"http://{host}:17665/mgmt/bpl/getApplianceInfo",
        json=data,
        status=200,
    )
    data_url = archiver.data_url()
    assert len(responses.calls) == 1
    assert data_url == "http://archiver-01:17668/retrieval/data/getData.raw"
    # data_url shall be cached
    _ = archiver.data_url()
    assert len(responses.calls) == 1


@responses.activate
def test_data_url_with_no_specific_port() -> None:
    archiver = ArchiverRetrieval("archiver-01.example.com")
    data = {"dataRetrievalURL": "http://archiver-01/foo"}
    responses.add(
        responses.GET,
        "http://archiver-01.example.com:17665/mgmt/bpl/getApplianceInfo",
        json=data,
        status=200,
    )
    data_url = archiver.data_url()
    assert len(responses.calls) == 1
    assert data_url == "http://archiver-01/foo/data/getData.raw"
