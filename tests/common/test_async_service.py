"""Tests for `service` package."""

import json
import logging

import pytest
from aioresponses import aioresponses
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
async def test_request_get_status_ok() -> None:
    url = "http://localhost"
    service = ServiceClient(url)
    data = {"test": "hello"}
    with aioresponses() as mocked:
        mocked.get(url, body=json.dumps(data))
        r = await service._get("/")
        assert await r.json() == data
        await service.close()


@pytest.mark.asyncio
async def test_request_raise_exception() -> None:
    url = "http://test.example.com"
    with aioresponses() as mocked:
        mocked.get(url, status=404)
        with pytest.raises(ArchiverResponseError):
            async with ServiceClient(url) as service:
                await service._get(url)


@pytest.mark.parametrize(
    "endpoint",
    ["endpoint", "/endpoint"],
)
@pytest.mark.asyncio
async def test_get_relative_endpoint(endpoint: str) -> None:
    url = "http://service.example.com/endpoint"
    with aioresponses() as mocked:
        mocked.get(url)
        async with ServiceClient("http://service.example.com") as service:
            await service._get(endpoint)
            mocked.assert_any_call(url)


@pytest.mark.asyncio
async def test_get_absolute_endpoint() -> None:
    url = "http://service.another.com:17667/this/is/a/test"
    with aioresponses() as mocked:
        mocked.get(url, status=200)
        async with ServiceClient("http://service.example.com") as service:
            await service._get(url)
            mocked.assert_any_call(url)


@pytest.mark.asyncio
async def test_get_return_response() -> None:
    url = f"http://service.example.com:{DEFAULT_RETRIEVAL_PORT}/my/endpoint"
    data = {"test": "hello"}
    with aioresponses() as mocked:
        mocked.get(url, body=json.dumps(data), status=200)
        base_url = f"http://service.example.com:{DEFAULT_RETRIEVAL_PORT}"
        async with ServiceClient(base_url) as service:
            r = await service._get("/my/endpoint")
            mocked.assert_any_call(url)
            assert await r.json() == data


@pytest.mark.asyncio
async def test_post_return_response() -> None:
    url = "http://test.example.com"
    data = {"test": "hello"}
    with aioresponses() as mocked:
        mocked.post(url, body=json.dumps(data), status=200)
        async with ServiceClient("test.example.com") as service:
            r = await service._post(url)
            mocked.assert_any_call(url, method="POST")
            assert await r.json() == data


@pytest.mark.parametrize(
    "endpoint",
    ["endpoint", "/endpoint"],
)
@pytest.mark.asyncio
async def test_post_relative_endpoint(endpoint: str) -> None:
    url = "http://service.example.com/endpoint"
    with aioresponses() as mocked:
        mocked.post(url, status=200)
        async with ServiceClient("http://service.example.com") as service:
            await service._post(endpoint)
            mocked.assert_any_call(url, method="POST")
