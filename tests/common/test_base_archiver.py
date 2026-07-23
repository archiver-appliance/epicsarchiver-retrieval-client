"""Tests for `epicsarchiver` package."""

import logging

import httpx
import pytest
import respx
from rich.logging import RichHandler

from epicsarchiver.common.base_archiver import (
    DEFAULT_RETRIEVAL_PORT,
    BaseArchiverAppliance,
)
from epicsarchiver.common.errors import ArchiverResponseError

logging.basicConfig(
    level=logging.DEBUG,
    handlers=[RichHandler(rich_tracebacks=True)],
)
LOG: logging.Logger = logging.getLogger(__name__)


def test_epicsarchiver_url() -> None:
    """Test the CLI."""
    archiver = BaseArchiverAppliance()
    assert archiver._base_url == f"http://localhost:{DEFAULT_RETRIEVAL_PORT}"
    archiver = BaseArchiverAppliance("archiver-01.example.com", port=80)
    assert archiver._base_url == "http://archiver-01.example.com:80"


@respx.mock
def test_get_raise_exception() -> None:
    archiver = BaseArchiverAppliance()
    url = "http://test.example.com"
    route = respx.get(url).mock(return_value=httpx.Response(404))
    with pytest.raises(ArchiverResponseError):
        archiver._get(url, params={})
    assert route.call_count == 1


@respx.mock
def test_get_relative_endpoint() -> None:
    archiver = BaseArchiverAppliance("archiver.example.com", port=17665)
    url = "http://archiver.example.com:17665/endpoint"
    route = respx.get(url).mock(return_value=httpx.Response(200))
    archiver._get("endpoint", params={})
    assert route.call_count == 1
    archiver._get("/endpoint", params={})
    assert route.call_count == 2


@respx.mock
def test_get_absolute_endpoint() -> None:
    archiver = BaseArchiverAppliance("archiver.example.com")
    url = "http://archiver.another.com:17667/this/is/a/test"
    route = respx.get(url).mock(return_value=httpx.Response(200))
    archiver._get(url, params={})
    assert route.call_count == 1


@respx.mock
def test_get_return_response() -> None:
    archiver = BaseArchiverAppliance()
    url = "http://archiver.example.com:17665/my/endpoint"
    data = {"test": "hello"}
    route = respx.get(url).mock(return_value=httpx.Response(200, json=data))
    r = archiver._get(url, params={})
    assert route.call_count == 1
    assert r.json() == data
