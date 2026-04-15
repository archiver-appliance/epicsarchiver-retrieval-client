"""Tests for `epicsarchiver` package."""

import logging

import pytest
import responses
from rich.logging import RichHandler

from epicsarchiver.common.base_archiver import BaseArchiverAppliance
from epicsarchiver.common.errors import ArchiverResponseError

logging.basicConfig(
    level=logging.DEBUG,
    handlers=[RichHandler(rich_tracebacks=True)],
)
LOG: logging.Logger = logging.getLogger(__name__)


def test_epicsarchiver_url() -> None:
    """Test the CLI."""
    archiver = BaseArchiverAppliance()
    assert archiver.mgmt_url == "http://localhost:17665/mgmt/bpl/"
    archiver = BaseArchiverAppliance("archiver-01.example.com", port=80)
    assert archiver.mgmt_url == "http://archiver-01.example.com:80/mgmt/bpl/"


@responses.activate
def test_request_get_status_ok() -> None:
    archiver = BaseArchiverAppliance()
    url = "http://test.example.com"
    data = {"test": "hello"}
    responses.add(responses.GET, url, json=data, status=200)
    r = archiver._request("GET", url)
    assert len(responses.calls) == 1
    assert r.json() == data


@responses.activate
def test_request_raise_exception() -> None:
    archiver = BaseArchiverAppliance()
    url = "http://test.example.com"
    responses.add(responses.GET, url, status=404)
    with pytest.raises(ArchiverResponseError):
        archiver._request("GET", url)
    assert len(responses.calls) == 1


@responses.activate
def test_get_relative_endpoint() -> None:
    archiver = BaseArchiverAppliance("archiver.example.com")
    url = "http://archiver.example.com:17665/mgmt/bpl/endpoint"
    responses.add(
        responses.GET,
        url,
        status=200,
    )
    archiver._get("endpoint")
    assert len(responses.calls) == 1
    archiver._get("/endpoint")
    assert len(responses.calls) == 2


@responses.activate
def test_get_absolute_endpoint() -> None:
    archiver = BaseArchiverAppliance("archiver.example.com")
    url = "http://archiver.another.com:17667/this/is/a/test"
    responses.add(responses.GET, url, status=200)
    archiver._get(url)
    assert len(responses.calls) == 1


@responses.activate
def test_get_return_response() -> None:
    archiver = BaseArchiverAppliance()
    url = "http://archiver.example.com:17665/my/endpoint"
    data = {"test": "hello"}
    responses.add(responses.GET, url, json=data, status=200)
    r = archiver._get(url)
    assert len(responses.calls) == 1
    assert r.json() == data


@responses.activate
def test_post_return_response() -> None:
    archiver = BaseArchiverAppliance()
    url = "http://test.example.com"
    data = {"test": "hello"}
    responses.add(responses.POST, url, json=data, status=201)
    r = archiver._post(url)
    assert len(responses.calls) == 1
    assert r.json() == data


@responses.activate
def test_post_relative_endpoint() -> None:
    archiver = BaseArchiverAppliance("archiver.example.com")
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
    archiver = BaseArchiverAppliance("archiver-01.example.com")
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
    archiver = BaseArchiverAppliance("archiver-01.example.com")
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
def test_get_or_post_single_pv() -> None:
    archiver = BaseArchiverAppliance("archiver.example.org")
    data = ["1", "2", "3"]
    responses.add(
        responses.GET,
        "http://archiver.example.org:17665/mgmt/bpl/endpoint",
        json=data,
        status=200,
        match=[responses.matchers.query_string_matcher("pv=mypv")],
    )
    r = archiver._get_or_post("/endpoint", "mypv")
    assert len(responses.calls) == 1
    assert r == data


@responses.activate
def test_get_or_post_comma_separated_list() -> None:
    archiver = BaseArchiverAppliance("archiver.example.org")
    data = ["1", "2", "3"]
    responses.add(
        responses.POST,
        "http://archiver.example.org:17665/mgmt/bpl/endpoint",
        json=data,
        status=200,
    )
    pvs = "mypv1,mypv2"
    r = archiver._get_or_post("/endpoint", pvs)
    assert (
        len(responses.calls) == 1
    )  # ignore for https://github.com/getsentry/responses/pull/690

    assert responses.calls[0].request.body == pvs
    assert r == data
