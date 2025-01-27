"""Tests for `epicsarchiver` package."""

from __future__ import annotations

import logging

import responses

from epicsarchiver.mgmt.archiver_mgmt_info import ArchiverMgmtInfo

LOG: logging.Logger = logging.getLogger(__name__)

TEST_DOMAIN = "archiver.example.org"


@responses.activate
def test_get_all_expanded_pvs() -> None:
    archiver = ArchiverMgmtInfo(TEST_DOMAIN)
    data = ["1", "2", "3"]
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/getAllExpandedPVNames",
        json=data,
        status=200,
    )
    pvs = archiver.get_all_expanded_pvs()
    assert len(responses.calls) == 1
    assert pvs == data


@responses.activate
def test_get_all_pvs_no_argument() -> None:
    archiver = ArchiverMgmtInfo(TEST_DOMAIN)
    data = ["1", "2", "3"]
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/getAllPVs?limit=500",
        json=data,
        status=200,
        match_querystring=True,
    )
    pvs = archiver.get_all_pvs()
    assert len(responses.calls) == 1
    assert pvs == data


@responses.activate
def test_get_all_pvs_with_limit() -> None:
    archiver = ArchiverMgmtInfo(TEST_DOMAIN)
    data = ["1", "2", "3"]
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/getAllPVs?limit=1200",
        json=data,
        status=200,
        match_querystring=True,
    )
    pvs = archiver.get_all_pvs(limit=1200)
    assert len(responses.calls) == 1
    assert pvs == data


@responses.activate
def test_get_all_pvs_with_pv() -> None:
    archiver = ArchiverMgmtInfo(TEST_DOMAIN)
    data = ["1", "2", "3"]
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/getAllPVs?pv=KLYS*&limit=500",
        json=data,
        status=200,
        match_querystring=True,
    )
    pvs = archiver.get_all_pvs(pv_query="KLYS*")
    assert len(responses.calls) == 1
    assert pvs == data


@responses.activate
def test_get_all_pvs_with_regex() -> None:
    archiver = ArchiverMgmtInfo(TEST_DOMAIN)
    data = ["1", "2", "3"]
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/getAllPVs?regex=foo&limit=500",
        json=data,
        status=200,
        match_querystring=True,
    )
    pvs = archiver.get_all_pvs(regex="foo")
    assert len(responses.calls) == 1
    assert pvs == data


@responses.activate
def test_get_pv_status() -> None:
    archiver = ArchiverMgmtInfo(TEST_DOMAIN)
    data = [{"pvName": "mypv"}]
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/getPVStatus?pv=mypv",
        json=data,
        status=200,
        match_querystring=True,
    )
    pvs = archiver.get_pv_status("mypv")
    assert len(responses.calls) == 1
    assert pvs == data


@responses.activate
def test_get_pv_type_info() -> None:
    archiver = ArchiverMgmtInfo(TEST_DOMAIN)
    data = {
        "hostName": "idmz-ro-epics-gw-tn.esss.lu.se",
        "paused": "false",
        "creationTime": "2025-01-23T12:04:58.973Z",
        "lowerAlarmLimit": "NaN",
        "precision": "0.0",
        "lowerCtrlLimit": "10.0",
        "units": "degC",
        "computedBytesPerEvent": "18",
        "computedEventRate": "18.366667",
        "usePVAccess": "false",
        "computedStorageRate": "345.35",
        "modificationTime": "2025-01-23T12:04:58.973Z",
        "upperDisplayLimit": "150.0",
        "upperWarningLimit": "30.0",
        "DBRType": "DBR_SCALAR_DOUBLE",
        "dataStores": [
            "pb://localhost?name=STS&rootFolder=${ARCHAPPL_SHORT_TERM_FOLDER}&partitionGranularity=PARTITION_HOUR&consolidateOnShutdown=true",
            "pb://localhost?name=MTS&rootFolder=${ARCHAPPL_MEDIUM_TERM_FOLDER}&partitionGranularity=PARTITION_DAY&hold=2&gather=1",
            "pb://localhost?name=LTS&rootFolder=${ARCHAPPL_LONG_TERM_FOLDER}&partitionGranularity=PARTITION_YEAR",
        ],
        "upperAlarmLimit": "50.0",
        "userSpecifiedEventRate": "0.0",
        "policyName": "2HzPVs",
        "useDBEProperties": "false",
        "hasReducedDataSet": "false",
        "lowerWarningLimit": "NaN",
        "applianceIdentity": "localhost",
        "scalar": "true",
        "pvName": "DTL-020:EMR-TT-002:Temp",
        "upperCtrlLimit": "150.0",
        "lowerDisplayLimit": "10.0",
        "samplingPeriod": "1.0",
        "elementCount": "1",
        "samplingMethod": "MONITOR",
        "archiveFields": ["HIHI", "HIGH", "LOW", "LOLO", "LOPR", "HOPR"],
        "extraFields": {
            "ADEL": "0.0",
            "MDEL": "0.0",
            "SCAN": "Passive",
            "NAME": "DTL-020:EMR-TT-002:Temp",
            "RTYP": "ai",
        },
    }
    responses.add(
        responses.GET,
        f"http://{TEST_DOMAIN}:17665/mgmt/bpl/getPVTypeInfo?pv=mypv",
        json=data,
        status=200,
        match_querystring=True,
    )

    pvs = archiver.get_pv_type_info("mypv")

    assert len(responses.calls) == 1
    assert pvs == data
