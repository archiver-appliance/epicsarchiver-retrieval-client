"""Tests for `service` package."""

import logging

import httpx
import pytest
import respx
from rich.logging import RichHandler

from epicsarchiver.common.async_service import ServiceClient
from epicsarchiver.common.base_archiver import DEFAULT_RETRIEVAL_PORT
from epicsarchiver.common.errors import ArchiverResponseError

logging.basicConfig(
    level=logging.DEBUG,
    handlers=[RichHandler(rich_tracebacks=True)],
)
LOG: logging.Logger = logging.getLogger(__name__)


@pytest.mark.asyncio
@respx.mock
async def test_request_get_status_ok() -> None:
    url = "http://localhost"
    service = ServiceClient(url)
    data = {"test": "hello"}
    respx.get(url).mock(return_value=httpx.Response(200, json=data))
    r = await service._get("/")
    assert r.json() == data
    await service.close()


@pytest.mark.asyncio
@respx.mock
async def test_request_raise_exception() -> None:
    url = "http://test.example.com"
    respx.get(url).mock(return_value=httpx.Response(404))
    with pytest.raises(ArchiverResponseError):
        async with ServiceClient(url) as service:
            await service._get(url)


@pytest.mark.parametrize(
    "endpoint",
    ["endpoint", "/endpoint"],
)
@pytest.mark.asyncio
@respx.mock
async def test_get_relative_endpoint(endpoint: str) -> None:
    url = "http://service.example.com/endpoint"
    route = respx.get(url).mock(return_value=httpx.Response(200))
    async with ServiceClient("http://service.example.com") as service:
        await service._get(endpoint)
        assert route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_get_absolute_endpoint() -> None:
    url = "http://service.another.com:17667/this/is/a/test"
    route = respx.get(url).mock(return_value=httpx.Response(200))
    async with ServiceClient("http://service.example.com") as service:
        await service._get(url)
        assert route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_get_return_response() -> None:
    url = f"http://service.example.com:{DEFAULT_RETRIEVAL_PORT}/my/endpoint"
    data = {"test": "hello"}
    route = respx.get(url).mock(return_value=httpx.Response(200, json=data))
    base_url = f"http://service.example.com:{DEFAULT_RETRIEVAL_PORT}"
    async with ServiceClient(base_url) as service:
        r = await service._get("/my/endpoint")
        assert route.call_count == 1
        assert r.json() == data


@pytest.mark.asyncio
@respx.mock
async def test_post_return_response() -> None:
    url = "http://test.example.com"
    data = {"test": "hello"}
    route = respx.post(url).mock(return_value=httpx.Response(200, json=data))
    async with ServiceClient("test.example.com") as service:
        r = await service._post(url)
        assert route.call_count == 1
        assert r.json() == data


@pytest.mark.parametrize(
    "endpoint",
    ["endpoint", "/endpoint"],
)
@pytest.mark.asyncio
@respx.mock
async def test_post_relative_endpoint(endpoint: str) -> None:
    url = "http://service.example.com/endpoint"
    route = respx.post(url).mock(return_value=httpx.Response(200))
    async with ServiceClient("http://service.example.com") as service:
        await service._post(endpoint)
        assert route.call_count == 1
