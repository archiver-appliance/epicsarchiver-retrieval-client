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
