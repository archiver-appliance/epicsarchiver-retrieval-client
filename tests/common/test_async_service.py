"""Tests for `ServiceClient`."""

import logging
from unittest.mock import AsyncMock

import pytest
from aiohttp import web
from pytest_aiohttp import AiohttpClient
from pytest_mock import MockerFixture
from rich.logging import RichHandler

from epicsarchiver.common.async_service import ServiceClient
from epicsarchiver.common.base_archiver import DEFAULT_RETRIEVAL_PORT
from epicsarchiver.common.errors import ArchiverResponseError

logging.basicConfig(
    level=logging.DEBUG,
    handlers=[RichHandler(rich_tracebacks=True)],
)
LOG: logging.Logger = logging.getLogger(__name__)


def _make_app() -> web.Application:
    app = web.Application()

    async def get_handler(_request: web.Request) -> web.Response:  # noqa: RUF029 keep mocking async
        return web.json_response({"method": "GET"})

    async def post_handler(_request: web.Request) -> web.Response:  # noqa: RUF029 keep mocking async
        return web.json_response({"method": "POST"})

    app.router.add_get("/data", get_handler)
    app.router.add_post("/data", post_handler)
    return app


def _mock_response(data: object = None) -> AsyncMock:
    response = AsyncMock()
    if data is not None:
        response.json = AsyncMock(return_value=data)
    return response


@pytest.fixture
def mock_session(mocker: MockerFixture) -> AsyncMock:
    session = AsyncMock()
    session.close = AsyncMock()
    mocker.patch(
        "epicsarchiver.common.async_service.ClientSession", return_value=session
    )
    return session


# --- Real HTTP tests ---


@pytest.mark.asyncio
async def test_get_returns_response(aiohttp_client: AiohttpClient) -> None:
    client = await aiohttp_client(_make_app())
    async with ServiceClient(str(client.make_url("/"))) as service:
        response = await service._get("/data")
        assert await response.json() == {"method": "GET"}


@pytest.mark.asyncio
async def test_post_returns_response(aiohttp_client: AiohttpClient) -> None:
    client = await aiohttp_client(_make_app())
    async with ServiceClient(str(client.make_url("/"))) as service:
        response = await service._post("/data")
        assert await response.json() == {"method": "POST"}


@pytest.mark.asyncio
async def test_404_raises_archiver_response_error(
    aiohttp_client: AiohttpClient,
) -> None:
    client = await aiohttp_client(_make_app())
    async with ServiceClient(str(client.make_url("/"))) as service:
        with pytest.raises(ArchiverResponseError):
            await service._get("/missing")


# --- URL construction tests (mock-based) ---


@pytest.mark.parametrize("endpoint", ["endpoint", "/endpoint"])
@pytest.mark.asyncio
async def test_get_relative_endpoint(endpoint: str, mock_session: AsyncMock) -> None:
    expected_url = f"http://service.example.com:{DEFAULT_RETRIEVAL_PORT}/endpoint"
    mock_session.get = AsyncMock(return_value=_mock_response())
    url = f"http://service.example.com:{DEFAULT_RETRIEVAL_PORT}"
    async with ServiceClient(url) as service:
        await service._get(endpoint)
        assert mock_session.get.call_args[0][0] == expected_url


@pytest.mark.asyncio
async def test_get_absolute_endpoint(mock_session: AsyncMock) -> None:
    url = "http://service.another.com:17667/this/is/a/test"
    mock_session.get = AsyncMock(return_value=_mock_response())
    async with ServiceClient("http://service.example.com") as service:
        await service._get(url)
        assert mock_session.get.call_args[0][0] == url
