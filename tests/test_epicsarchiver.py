# -*- coding: utf-8 -*-
"""Tests for `epicsarchiver` package."""
import json
import pytest
import requests
import responses
import pandas as pd
from epicsarchiver import ArchiverAppliance


def test_epicsarchiver_url():
    """Test the CLI."""
    archiver = ArchiverAppliance()
    assert archiver.mgmt_url == "http://localhost:17665/mgmt/bpl/"
    archiver = ArchiverAppliance("archiver-01.example.com", port=80)
    assert archiver.mgmt_url == "http://archiver-01.example.com:80/mgmt/bpl/"


@responses.activate
def test_request_get_status_ok():
    archiver = ArchiverAppliance()
    url = "http://test.example.com"
    data = {"test": "hello"}
    responses.add(responses.GET, url, json=data, status=200)
    r = archiver.request("GET", url)
    assert len(responses.calls) == 1
    assert r.json() == data


@responses.activate
def test_request_raise_exception():
    archiver = ArchiverAppliance()
    url = "http://test.example.com"
    responses.add(responses.GET, url, status=404)
    with pytest.raises(requests.exceptions.HTTPError):
        archiver.request("GET", url)
    assert len(responses.calls) == 1


@responses.activate
def test_get_relative_endpoint():
    archiver = ArchiverAppliance("archiver.example.com")
    responses.add(
        responses.GET, "http://archiver.example.com:17665/mgmt/bpl/endpoint", status=200
    )
    archiver.get("endpoint")
    assert len(responses.calls) == 1
    archiver.get("/endpoint")
    assert len(responses.calls) == 2


@responses.activate
def test_get_absolute_endpoint():
    archiver = ArchiverAppliance("archiver.example.com")
    url = "http://archiver.another.com:17667/this/is/a/test"
    responses.add(responses.GET, url, status=200)
    archiver.get(url)
    assert len(responses.calls) == 1


@responses.activate
def test_get_return_response():
    archiver = ArchiverAppliance()
    url = "http://archiver.example.com:17665/my/endpoint"
    data = {"test": "hello"}
    responses.add(responses.GET, url, json=data, status=200)
    r = archiver.get(url)
    assert len(responses.calls) == 1
    assert r.json() == data


@responses.activate
def test_post_return_response():
    archiver = ArchiverAppliance()
    url = "http://test.example.com"
    data = {"test": "hello"}
    responses.add(responses.POST, url, json=data, status=201)
    r = archiver.post(url)
    assert len(responses.calls) == 1
    assert r.json() == data


@responses.activate
def test_post_relative_endpoint():
    archiver = ArchiverAppliance("archiver.example.com")
    responses.add(
        responses.POST,
        "http://archiver.example.com:17665/mgmt/bpl/endpoint",
        status=201,
    )
    archiver.post("endpoint")
    assert len(responses.calls) == 1
    archiver.post("/endpoint")
    assert len(responses.calls) == 2


@responses.activate
def test_info():
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
    archiver.info
    assert len(responses.calls) == 1


@responses.activate
def test_identity_and_version():
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
def test_data_url_with_same_archiver_host(host):
    archiver = ArchiverAppliance(host)
    data = {"dataRetrievalURL": "http://archiver-01:17668/retrieval"}
    responses.add(
        responses.GET,
        f"http://{host}:17665/mgmt/bpl/getApplianceInfo",
        json=data,
        status=200,
    )
    data_url = archiver.data_url
    assert len(responses.calls) == 1
    assert data_url == f"http://archiver-01:17668/retrieval/data/getData.json"
    # data_url shall be cached
    archiver.data_url
    assert len(responses.calls) == 1


@responses.activate
def test_data_url_with_no_specific_port():
    archiver = ArchiverAppliance("archiver-01.example.com")
    data = {"dataRetrievalURL": "http://archiver-01/foo"}
    responses.add(
        responses.GET,
        "http://archiver-01.example.com:17665/mgmt/bpl/getApplianceInfo",
        json=data,
        status=200,
    )
    data_url = archiver.data_url
    assert len(responses.calls) == 1
    assert data_url == "http://archiver-01/foo/data/getData.json"


@responses.activate
def test_get_all_expanded_pvs():
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
def test_get_all_pvs_no_argument():
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
def test_get_all_pvs_with_limit():
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
def test_get_all_pvs_with_pv():
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
def test_get_all_pvs_with_regex():
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
def test_get_pv_status():
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
def test_archive_pv():
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
def test_archive_pv_with_extra_args():
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
def test_archive_pvs():
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
def test_archive_pvs_from_files(tmpdir):
    # Create 2 files with some PVs
    pvs1 = [
        {"pv": "LEBT-010:PwrC-SolPS-01:CurS"},
        {"pv": "LEBT-010:ID-Iris:OFFSET_Y_SET"},
    ]
    tmp = tmpdir.mkdir("archiver01")
    file1 = tmp.join("file1.archive")
    file1.write("\n".join([item["pv"] for item in pvs1]))
    pvs2 = [{"pv": "LEBT-010:PBI-NPM-001:HCAM-COM", "policy": "slow"}]
    file2 = tmp.join("file2")
    file2.write(pvs2[0]["pv"] + " " + pvs2[0]["policy"] + "\n")
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
def test_get_or_post_single_pv():
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
def test_get_or_post_comma_separated_list():
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
def test_pause_pv_single():
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
def test_pause_pv_comma_separated_list():
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
def test_resume_pv_single():
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
def test_resume_pv_comma_separated_list():
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
def test_abort_pv():
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
def test_delete_pv_data_false():
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
def test_delete_pv_data_true():
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
def test_update_pv():
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
def test_update_pv_samplingmethod():
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


@responses.activate
def test_get_data():
    host = "archiver.example.org"
    archiver = ArchiverAppliance(host)
    pv = "mypv"
    data = [
        {
            "meta": {"name": "mypv", "EGU": "mA", "PREC": "2"},
            "data": [
                {
                    "secs": 1537302383,
                    "val": 1,
                    "nanos": 931598267,
                    "severity": 0,
                    "status": 0,
                },
                {
                    "secs": 1537302384,
                    "val": 2,
                    "nanos": 907631989,
                    "severity": 0,
                    "status": 0,
                },
                {
                    "secs": 1537302385,
                    "val": 3,
                    "nanos": 909627429,
                    "severity": 0,
                    "status": 0,
                },
                {
                    "secs": 1537302386,
                    "val": 4,
                    "nanos": 911606448,
                    "severity": 0,
                    "status": 0,
                },
            ],
        }
    ]
    dates = pd.DatetimeIndex(
        [
            "2018-09-18 20:26:23.931598186",
            "2018-09-18 20:26:24.907631874",
            "2018-09-18 20:26:25.909627438",
            "2018-09-18 20:26:26.911606550",
        ]
    )
    ref_df = pd.DataFrame([1, 2, 3, 4], index=dates)
    ref_df = ref_df.rename_axis("date")
    ref_df.columns = ["val"]
    responses.add(
        responses.GET,
        f"http://{host}:17665/mgmt/bpl/getApplianceInfo",
        json={"dataRetrievalURL": "http://archiver-01:17668/retrieval"},
        status=200,
    )
    responses.add(
        responses.GET,
        f"http://archiver-01:17668/retrieval/data/getData.json?pv={pv}&from=2018-08-25T17%3A45%3A00.000000Z&to=2018-08-25T18%3A45%3A00.000000Z",
        json=data,
        status=200,
        match_querystring=True,
    )
    df = archiver.get_data(pv, "20180825 17:45", "20180825 18:45")
    assert len(responses.calls) == 2
    pd.testing.assert_frame_equal(ref_df, df)
