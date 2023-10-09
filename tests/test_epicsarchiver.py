"""Tests for `epicsarchiver` package."""
import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest
import requests
import responses
from pytz import utc as UTC  # noqa: N812
from rich.logging import RichHandler

from epicsarchiver import ArchiveEvent, ArchiverAppliance, FieldValue, epicsarchiver
from epicsarchiver.EPICSEvent_pb2 import SCALAR_INT, PayloadInfo, ScalarInt
from epicsarchiver.EPICSEvent_pb2 import FieldValue as eeFieldValue
from epicsarchiver.pb import (
    create_pb_bytes,
    year_timestamp,
)

logging.basicConfig(
    level=logging.DEBUG,
    handlers=[RichHandler(rich_tracebacks=True)],
)
LOG: logging.Logger = logging.getLogger(__name__)


def test_epicsarchiver_url() -> None:
    """Test the CLI."""
    archiver = ArchiverAppliance()
    assert archiver.mgmt_url == "http://localhost:17665/mgmt/bpl/"
    archiver = ArchiverAppliance("archiver-01.example.com", port=80)
    assert archiver.mgmt_url == "http://archiver-01.example.com:80/mgmt/bpl/"


@responses.activate
def test_request_get_status_ok() -> None:
    archiver = ArchiverAppliance()
    url = "http://test.example.com"
    data = {"test": "hello"}
    responses.add(responses.GET, url, json=data, status=200)
    r = archiver._request("GET", url)
    assert len(responses.calls) == 1
    assert r.json() == data


@responses.activate
def test_request_raise_exception() -> None:
    archiver = ArchiverAppliance()
    url = "http://test.example.com"
    responses.add(responses.GET, url, status=404)
    with pytest.raises(requests.exceptions.HTTPError):
        archiver._request("GET", url)
    assert len(responses.calls) == 1


@responses.activate
def test_get_relative_endpoint() -> None:
    archiver = ArchiverAppliance("archiver.example.com")
    responses.add(
        responses.GET, "http://archiver.example.com:17665/mgmt/bpl/endpoint", status=200
    )
    archiver._get("endpoint")
    assert len(responses.calls) == 1
    archiver._get("/endpoint")
    assert len(responses.calls) == 2


@responses.activate
def test_get_absolute_endpoint() -> None:
    archiver = ArchiverAppliance("archiver.example.com")
    url = "http://archiver.another.com:17667/this/is/a/test"
    responses.add(responses.GET, url, status=200)
    archiver._get(url)
    assert len(responses.calls) == 1


@responses.activate
def test_get_return_response() -> None:
    archiver = ArchiverAppliance()
    url = "http://archiver.example.com:17665/my/endpoint"
    data = {"test": "hello"}
    responses.add(responses.GET, url, json=data, status=200)
    r = archiver._get(url)
    assert len(responses.calls) == 1
    assert r.json() == data


@responses.activate
def test_post_return_response() -> None:
    archiver = ArchiverAppliance()
    url = "http://test.example.com"
    data = {"test": "hello"}
    responses.add(responses.POST, url, json=data, status=201)
    r = archiver._post(url)
    assert len(responses.calls) == 1
    assert r.json() == data


@responses.activate
def test_post_relative_endpoint() -> None:
    archiver = ArchiverAppliance("archiver.example.com")
    responses.add(
        responses.POST,
        "http://archiver.example.com:17665/mgmt/bpl/endpoint",
        status=201,
    )
    archiver._post("endpoint")
    assert len(responses.calls) == 1
    archiver._post("/endpoint")
    assert len(responses.calls) == 2


@responses.activate
def test_info() -> None:
    archiver = ArchiverAppliance("archiver-01.example.com")
    data = {
        "engineURL": "http://archiver-01:17666/engine/bpl",
        "identity": "appliance0",
    }
    responses.add(
        responses.GET,
        "http://archiver-01.example.com:17665/mgmt/bpl/getApplianceInfo",
        json=data,
        status=200,
    )
    info = archiver.info
    assert len(responses.calls) == 1
    assert info == data
    # info shall be cached - no more calls
    _ = archiver.info
    assert len(responses.calls) == 1


@responses.activate
def test_identity_and_version() -> None:
    archiver = ArchiverAppliance("archiver-01.example.com")
    data = {"identity": "appliance0", "version": "v1.0.0"}
    responses.add(
        responses.GET,
        "http://archiver-01.example.com:17665/mgmt/bpl/getApplianceInfo",
        json=data,
        status=200,
    )
    identity = archiver.identity
    assert len(responses.calls) == 1
    assert identity == "appliance0"
    version = archiver.version
    # No extra call
    assert len(responses.calls) == 1
    assert version == "v1.0.0"


@responses.activate
@pytest.mark.parametrize("host", ["archiver-01.example.com", "192.168.4.75"])
def test_data_url_with_same_archiver_host(host: str) -> None:
    archiver = ArchiverAppliance(host)
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
    archiver = ArchiverAppliance("archiver-01.example.com")
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


@responses.activate
def test_get_all_expanded_pvs() -> None:
    archiver = ArchiverAppliance("archiver.example.org")
    data = [1, 2, 3]
    responses.add(
        responses.GET,
        "http://archiver.example.org:17665/mgmt/bpl/getAllExpandedPVNames",
        json=data,
        status=200,
    )
    pvs = archiver.get_all_expanded_pvs()
    assert len(responses.calls) == 1
    assert pvs == data


@responses.activate
def test_get_all_pvs_no_argument() -> None:
    archiver = ArchiverAppliance("archiver.example.org")
    data = [1, 2, 3]
    responses.add(
        responses.GET,
        "http://archiver.example.org:17665/mgmt/bpl/getAllPVs?limit=500",
        json=data,
        status=200,
        match_querystring=True,
    )
    pvs = archiver.get_all_pvs()
    assert len(responses.calls) == 1
    assert pvs == data


@responses.activate
def test_get_all_pvs_with_limit() -> None:
    archiver = ArchiverAppliance("archiver.example.org")
    data = [1, 2, 3]
    responses.add(
        responses.GET,
        "http://archiver.example.org:17665/mgmt/bpl/getAllPVs?limit=1200",
        json=data,
        status=200,
        match_querystring=True,
    )
    pvs = archiver.get_all_pvs(limit=1200)
    assert len(responses.calls) == 1
    assert pvs == data


@responses.activate
def test_get_all_pvs_with_pv() -> None:
    archiver = ArchiverAppliance("archiver.example.org")
    data = [1, 2, 3]
    responses.add(
        responses.GET,
        "http://archiver.example.org:17665/mgmt/bpl/getAllPVs?pv=KLYS*&limit=500",
        json=data,
        status=200,
        match_querystring=True,
    )
    pvs = archiver.get_all_pvs(pv="KLYS*")
    assert len(responses.calls) == 1
    assert pvs == data


@responses.activate
def test_get_all_pvs_with_regex() -> None:
    archiver = ArchiverAppliance("archiver.example.org")
    data = [1, 2, 3]
    responses.add(
        responses.GET,
        "http://archiver.example.org:17665/mgmt/bpl/getAllPVs?regex=foo&limit=500",
        json=data,
        status=200,
        match_querystring=True,
    )
    pvs = archiver.get_all_pvs(regex="foo")
    assert len(responses.calls) == 1
    assert pvs == data


@responses.activate
def test_get_pv_status() -> None:
    archiver = ArchiverAppliance("archiver.example.org")
    data = [{"pvName": "mypv"}]
    responses.add(
        responses.GET,
        "http://archiver.example.org:17665/mgmt/bpl/getPVStatus?pv=mypv",
        json=data,
        status=200,
        match_querystring=True,
    )
    pvs = archiver.get_pv_status("mypv")
    assert len(responses.calls) == 1
    assert pvs == data


@responses.activate
def test_archive_pv() -> None:
    archiver = ArchiverAppliance("archiver.example.org")
    data = [
        {"pvName": "ISrc-010:HVAC-HT:AmbHumR", "status": "Archive request submitted"}
    ]
    responses.add(
        responses.GET,
        "http://archiver.example.org:17665/mgmt/bpl/archivePV?pv=ISrc-010%3AHVAC-HT%3AAmbHumR",
        json=data,
        status=200,
        match_querystring=True,
    )
    r = archiver.archive_pv("ISrc-010:HVAC-HT:AmbHumR")
    assert len(responses.calls) == 1
    assert r == data


@responses.activate
def test_archive_pv_with_extra_args() -> None:
    archiver = ArchiverAppliance("archiver.example.org")
    data = [
        {"pvName": "ISrc-010:HVAC-HT:AmbHumR", "status": "Archive request submitted"}
    ]
    responses.add(
        responses.GET,
        "http://archiver.example.org:17665/mgmt/bpl/archivePV?pv=ISrc-010%3AHVAC-HT%3AAmbHumR&samplingperiod=2.0&samplingmethod=SCAN",
        json=data,
        status=200,
        match_querystring=True,
    )
    r = archiver.archive_pv(
        "ISrc-010:HVAC-HT:AmbHumR", samplingperiod=2.0, samplingmethod="SCAN"
    )
    assert len(responses.calls) == 1
    assert r == data


@responses.activate
def test_archive_pvs() -> None:
    archiver = ArchiverAppliance("archiver.example.org")
    data = [1, 2, 3]
    responses.add(
        responses.POST,
        "http://archiver.example.org:17665/mgmt/bpl/archivePV",
        json=data,
        status=200,
    )
    pvs = [{"pv": "first:pv"}, {"pv": "second:pv"}]
    r = archiver.archive_pvs(pvs)
    assert len(responses.calls) == 1
    body = json.loads(responses.calls[0].request.body.decode("utf-8"))
    assert body == pvs
    assert r == data


@responses.activate
def test_archive_pvs_from_files(tmp_path: Path) -> None:
    # Create 2 files with some PVs
    pvs1 = [
        {"pv": "LEBT-010:PwrC-SolPS-01:CurS"},
        {"pv": "LEBT-010:ID-Iris:OFFSET_Y_SET"},
    ]
    tmp = tmp_path.joinpath("archiver01")
    tmp.mkdir()
    file1 = tmp.joinpath("file1.archive")
    file1.open("w").write("\n".join([item["pv"] for item in pvs1]))
    pvs2 = [{"pv": "LEBT-010:PBI-NPM-001:HCAM-COM", "policy": "slow"}]
    file2 = tmp.joinpath("file2")
    file2.open("w").write(pvs2[0]["pv"] + " " + pvs2[0]["policy"] + "\n")
    archiver = ArchiverAppliance("archiver.example.org")
    data = [1, 2, 3]
    responses.add(
        responses.POST,
        "http://archiver.example.org:17665/mgmt/bpl/archivePV",
        json=data,
        status=200,
    )
    r = archiver.archive_pvs_from_files([str(file1), str(file2)])
    assert len(responses.calls) == 1
    body = json.loads(responses.calls[0].request.body.decode("utf-8"))
    assert body == pvs1 + pvs2
    assert r == data
    # With appliance as parameter
    r = archiver.archive_pvs_from_files(
        [str(file1), str(file2)], appliance="appliance0"
    )
    body = json.loads(responses.calls[1].request.body.decode("utf-8"))
    pvs = pvs1 + pvs2
    for pv in pvs:
        pv["appliance"] = "appliance0"
    assert body == pvs


@responses.activate
def test_get_or_post_single_pv() -> None:
    archiver = ArchiverAppliance("archiver.example.org")
    data = [1, 2, 3]
    responses.add(
        responses.GET,
        "http://archiver.example.org:17665/mgmt/bpl/endpoint?pv=mypv",
        json=data,
        status=200,
        match_querystring=True,
    )
    r = archiver._get_or_post("/endpoint", "mypv")
    assert len(responses.calls) == 1
    assert r == data


@responses.activate
def test_get_or_post_comma_separated_list() -> None:
    archiver = ArchiverAppliance("archiver.example.org")
    data = [1, 2, 3]
    responses.add(
        responses.POST,
        "http://archiver.example.org:17665/mgmt/bpl/endpoint",
        json=data,
        status=200,
        match_querystring=True,
    )
    pvs = "mypv1,mypv2"
    r = archiver._get_or_post("/endpoint", pvs)
    assert len(responses.calls) == 1
    assert responses.calls[0].request.body == pvs
    assert r == data


@responses.activate
def test_pause_pv_single() -> None:
    archiver = ArchiverAppliance("archiver.example.org")
    data = [1, 2, 3]
    pv = "KLYS*"
    responses.add(
        responses.GET,
        f"http://archiver.example.org:17665/mgmt/bpl/pauseArchivingPV?pv={pv}",
        json=data,
        status=200,
        match_querystring=True,
    )
    r = archiver.pause_pv(pv)
    assert len(responses.calls) == 1
    assert r == data


@responses.activate
def test_pause_pv_comma_separated_list() -> None:
    archiver = ArchiverAppliance("archiver.example.org")
    data = [1, 2, 3]
    pvs = "mypv1,mypv2"
    responses.add(
        responses.POST,
        "http://archiver.example.org:17665/mgmt/bpl/pauseArchivingPV",
        json=data,
        status=200,
        match_querystring=True,
    )
    r = archiver.pause_pv(pvs)
    assert len(responses.calls) == 1
    assert responses.calls[0].request.body == pvs
    assert r == data


@responses.activate
def test_resume_pv_single() -> None:
    archiver = ArchiverAppliance("archiver.example.org")
    data = [1, 2, 3]
    pv = "KLYS*"
    responses.add(
        responses.GET,
        f"http://archiver.example.org:17665/mgmt/bpl/resumeArchivingPV?pv={pv}",
        json=data,
        status=200,
        match_querystring=True,
    )
    r = archiver.resume_pv(pv)
    assert len(responses.calls) == 1
    assert r == data


@responses.activate
def test_resume_pv_comma_separated_list() -> None:
    archiver = ArchiverAppliance("archiver.example.org")
    data = [1, 2, 3]
    pvs = "mypv1,mypv2"
    responses.add(
        responses.POST,
        "http://archiver.example.org:17665/mgmt/bpl/resumeArchivingPV",
        json=data,
        status=200,
        match_querystring=True,
    )
    r = archiver.resume_pv(pvs)
    assert len(responses.calls) == 1
    assert responses.calls[0].request.body == pvs
    assert r == data


@responses.activate
def test_abort_pv() -> None:
    archiver = ArchiverAppliance("archiver.example.org")
    data = [1, 2, 3]
    pv = "LEBT-010:PBI-NPM-001:HCAM-COM"
    responses.add(
        responses.GET,
        "http://archiver.example.org:17665/mgmt/bpl/abortArchivingPV?pv=LEBT-010%3APBI-NPM-001%3AHCAM-COM",
        json=data,
        status=200,
        match_querystring=True,
    )
    r = archiver.abort_pv(pv)
    assert len(responses.calls) == 1
    assert r == data


@responses.activate
def test_delete_pv_data_false() -> None:
    archiver = ArchiverAppliance("archiver.example.org")
    data = [1, 2, 3]
    pv = "LEBT-010:PBI-NPM-001:HCAM-COM"
    responses.add(
        responses.GET,
        "http://archiver.example.org:17665/mgmt/bpl/deletePV?pv=LEBT-010%3APBI-NPM-001%3AHCAM-COM&delete_data=False",
        json=data,
        status=200,
        match_querystring=True,
    )
    r = archiver.delete_pv(pv)
    assert len(responses.calls) == 1
    assert r == data


@responses.activate
def test_delete_pv_data_true() -> None:
    archiver = ArchiverAppliance("archiver.example.org")
    data = [1, 2, 3]
    pv = "LEBT-010:PBI-NPM-001:HCAM-COM"
    responses.add(
        responses.GET,
        "http://archiver.example.org:17665/mgmt/bpl/deletePV?pv=LEBT-010%3APBI-NPM-001%3AHCAM-COM&delete_data=True",
        json=data,
        status=200,
        match_querystring=True,
    )
    r = archiver.delete_pv(pv, delete_data=True)
    assert len(responses.calls) == 1
    assert r == data


@responses.activate
def test_update_pv() -> None:
    archiver = ArchiverAppliance("archiver.example.org")
    data = [1, 2, 3]
    pv = "mypv"
    responses.add(
        responses.GET,
        f"http://archiver.example.org:17665/mgmt/bpl/changeArchivalParameters?pv={pv}&samplingperiod=2.0",
        json=data,
        status=200,
        match_querystring=True,
    )
    r = archiver.update_pv(pv, 2.0)
    assert len(responses.calls) == 1
    assert r == data


@responses.activate
def test_update_pv_samplingmethod() -> None:
    archiver = ArchiverAppliance("archiver.example.org")
    data = [1, 2, 3]
    pv = "mypv"
    responses.add(
        responses.GET,
        f"http://archiver.example.org:17665/mgmt/bpl/changeArchivalParameters?pv={pv}&samplingperiod=2.0&samplingmethod=SCAN",
        json=data,
        status=200,
        match_querystring=True,
    )
    r = archiver.update_pv(pv, 2.0, "SCAN")
    assert len(responses.calls) == 1
    assert r == data


TEST_EVENTS = [
    ScalarInt(
        secondsintoyear=22537583,
        val=1,
        nano=931598267,
        severity=0,
        status=0,
        fieldvalues=[eeFieldValue(name="hey", val="ho")],
    ),
    ScalarInt(
        secondsintoyear=22537584,
        val=2,
        nano=907631989,
        severity=0,
        status=0,
        fieldvalues=[eeFieldValue(name="hey", val="ho")],
    ),
    ScalarInt(
        secondsintoyear=22537585,
        val=3,
        nano=931598267,
        severity=0,
        status=0,
        fieldvalues=[eeFieldValue(name="hey", val="ho")],
    ),
    ScalarInt(
        secondsintoyear=22537586,
        val=4,
        nano=911606448,
        severity=0,
        status=0,
        fieldvalues=[eeFieldValue(name="hey", val="ho")],
    ),
]


@responses.activate
def test_get_data() -> None:
    host = "archiver.example.org"
    archiver = ArchiverAppliance(host)
    pv = "mypv"
    events = TEST_EVENTS
    dates = [
        pd.Timestamp((year_timestamp(2018) + d.secondsintoyear) * 1e9 + d.nano, tz=UTC)
        for d in events
    ]
    pd_dates = pd.DatetimeIndex(
        dates,
        tz=UTC,
    )
    ref_df = pd.DataFrame([e.val for e in TEST_EVENTS], index=pd_dates)
    ref_df = ref_df.rename_axis("date")
    ref_df.columns = ["val"]  # type: ignore[assignment]
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
            events, PayloadInfo(type=SCALAR_INT, pvname=pv, year=2018)
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
    archiver = ArchiverAppliance(host)
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
            events, PayloadInfo(type=SCALAR_INT, pvname=pv, year=2018)
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
            [FieldValue.from_pb_field_value(f) for f in e.fieldvalues],
        )
        for e in events
    ]


@responses.activate
def test_pause_rename_resume_pv(caplog: pytest.LogCaptureFixture) -> None:
    archiver = ArchiverAppliance("archiver.example.org")
    pv = "MY:PV"
    newname = "NEW:PV"
    responses.add(
        responses.GET,
        f"http://archiver.example.org:17665/mgmt/bpl/getPVStatus?pv={pv}",
        json=[{"status": "Being archived"}],
        status=200,
        match_querystring=True,
    )
    responses.add(
        responses.GET,
        f"http://archiver.example.org:17665/mgmt/bpl/getPVStatus?pv={newname}",
        json=[{"status": "Not being archived"}],
        status=200,
        match_querystring=True,
    )
    responses.add(
        responses.GET,
        f"http://archiver.example.org:17665/mgmt/bpl/pauseArchivingPV?pv={pv}",
        json={"status": "ok"},
        status=200,
        match_querystring=True,
    )
    responses.add(
        responses.GET,
        f"http://archiver.example.org:17665/mgmt/bpl/renamePV?pv={pv}&newname={newname}",
        json={"status": "ok"},
        status=200,
        match_querystring=True,
    )
    responses.add(
        responses.GET,
        f"http://archiver.example.org:17665/mgmt/bpl/resumeArchivingPV?pv={newname}",
        json={"status": "ok"},
        status=200,
        match_querystring=True,
    )
    with caplog.at_level(logging.DEBUG):
        archiver.pause_rename_resume_pv(pv, newname)
    captured_log = caplog.text
    assert len(responses.calls) == 5
    assert f"PV {pv} successfully renamed to {newname}\n" in captured_log


@responses.activate
def test_pause_rename_resume_pv_not_archived_pv(
    caplog: pytest.LogCaptureFixture,
) -> None:
    archiver = ArchiverAppliance("archiver.example.org")
    pv = "MY:PV"
    newname = "NEW:PV"
    responses.add(
        responses.GET,
        f"http://archiver.example.org:17665/mgmt/bpl/getPVStatus?pv={pv}",
        json=[{"status": "Not being archived"}],
        status=200,
        match_querystring=True,
    )
    with caplog.at_level(logging.DEBUG):
        archiver.pause_rename_resume_pv(pv, newname)
    captured_log = caplog.text
    assert len(responses.calls) == 1
    assert f"PV {pv} isn't being archived. Skipping.\n" in captured_log


@responses.activate
def test_pause_rename_resume_pv_existing_new(caplog: pytest.LogCaptureFixture) -> None:
    archiver = ArchiverAppliance("archiver.example.org")
    pv = "MY:PV"
    newname = "NEW:PV"
    responses.add(
        responses.GET,
        f"http://archiver.example.org:17665/mgmt/bpl/getPVStatus?pv={pv}",
        json=[{"status": "Being archived"}],
        status=200,
        match_querystring=True,
    )
    responses.add(
        responses.GET,
        f"http://archiver.example.org:17665/mgmt/bpl/getPVStatus?pv={newname}",
        json=[{"status": "Being archived"}],
        status=200,
        match_querystring=True,
    )
    with caplog.at_level(logging.DEBUG):
        archiver.pause_rename_resume_pv(pv, newname)
    captured_log = caplog.text
    assert len(responses.calls) == 2
    assert f"New PV {newname} already exists. Skipping.\n" in captured_log


@responses.activate
def test_pause_rename_resume_pv_error_rename(caplog: pytest.LogCaptureFixture) -> None:
    archiver = ArchiverAppliance("archiver.example.org")
    pv = "MY:PV"
    newname = "NEW:PV"
    responses.add(
        responses.GET,
        f"http://archiver.example.org:17665/mgmt/bpl/getPVStatus?pv={pv}",
        json=[{"status": "Being archived"}],
        status=200,
        match_querystring=True,
    )
    responses.add(
        responses.GET,
        f"http://archiver.example.org:17665/mgmt/bpl/getPVStatus?pv={newname}",
        json=[{"status": "Not being archived"}],
        status=200,
        match_querystring=True,
    )
    responses.add(
        responses.GET,
        f"http://archiver.example.org:17665/mgmt/bpl/pauseArchivingPV?pv={pv}",
        json={"status": "ok"},
        status=200,
        match_querystring=True,
    )
    responses.add(
        responses.GET,
        f"http://archiver.example.org:17665/mgmt/bpl/renamePV?pv={pv}&newname={newname}",
        json={"validation": "error during rename"},
        status=200,
        match_querystring=True,
    )
    with caplog.at_level(logging.DEBUG):
        archiver.pause_rename_resume_pv(pv, newname)
    captured_log = caplog.text
    LOG.info(captured_log)
    assert len(responses.calls) == 4
    assert "error during rename" in captured_log


def test_format_date() -> None:
    assert epicsarchiver.format_date("20180715") == "2018-07-15T00:00:00.000000Z"
    assert epicsarchiver.format_date("20180715 17:45") == "2018-07-15T17:45:00.000000Z"
    assert (
        epicsarchiver.format_date(datetime(2018, 7, 15, 19, 5, tzinfo=UTC))
        == "2018-07-15T19:05:00.000000Z"
    )


@pytest.mark.parametrize(
    "test_input,expected",
    [({"status": "ok"}, True), ({"status": "foo"}, False), ({"hello": "world"}, False)],
)
def test_check_result(
    test_input: dict[str, str], expected: bool  # noqa: FBT001
) -> None:
    output = epicsarchiver.check_result(test_input)
    assert output is expected


@pytest.mark.parametrize(
    "test_input,default_message,output",
    [
        ({"status": "nok"}, "Not OK", "Not OK\n"),
        ({"validation": "Hello"}, None, "Hello\n"),
        ({"validation": "Hello"}, "foo", "Hello\n"),
    ],
)
def test_check_result_message(
    caplog: pytest.LogCaptureFixture,
    test_input: dict[str, str],
    default_message: str,
    output: str,
) -> None:
    with caplog.at_level(logging.ERROR):
        epicsarchiver.check_result(test_input, default_message)
    captured_log = caplog.text
    assert output in captured_log
