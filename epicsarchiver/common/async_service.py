"""Module to cover the ServiceClient for doing http calls."""

from __future__ import annotations

import logging
import urllib.parse
from typing import TYPE_CHECKING, Any

from aiohttp import ClientResponse, ClientSession
from typing_extensions import Self

if TYPE_CHECKING:
    from collections.abc import Mapping
    from types import TracebackType

LOG: logging.Logger = logging.getLogger(__name__)


class ServiceClient:
    """An async and sync http service client.

    For doing basic GET POST http calls.
    """

    def __init__(self, base_url: str) -> None:
        """Create Service object."""
        self.base_url = base_url
        self._session: ClientSession | None = None

    @property
    def session(self) -> ClientSession:
        """Return the aiohttp session.

        Returns:
            ClientSession: The session.
        """
        if not self._session:
            self._session = ClientSession()
        return self._session

    async def close(self) -> None:
        """Close the Service (closes the session)."""
        if self._session is not None:
            await self._session.close()

    async def __aenter__(self) -> Self:
        """Asynchronous enter.

        Returns:
            Self: self
        """
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Asynchronous exit, closes any sessions."""
        await self.close()

    async def _get(
        self, endpoint: str, params: Mapping[str, str] | None = None
    ) -> ClientResponse:
        """Send a GET request to the given endpoint.

        Args:
            endpoint: API endpoint (relative or absolute)
            params: parameters to be sent

        Returns:
            :class:`ClientResponse` object
        """
        url = urllib.parse.urljoin(self.base_url, endpoint.lstrip("/"))
        LOG.debug("GET url: %s", url)
        return await self.session.get(
            url, params=params, raise_for_status=True, ssl=False
        )

    async def _get_json(
        self, endpoint: str, params: Mapping[str, str] | None = None
    ) -> Any:
        """Send a GET request to the given endpoint and return the json.

        Args:
            endpoint: API endpoint (relative or absolute)
            params: parameters to be sent

        Returns:
            :class:`ClientResponse` object
        """
        async with await self._get(endpoint, params=params) as response:
            return await response.json()

    async def _post(
        self,
        endpoint: str,
        params: Mapping[str, str] | None = None,
        data: Any = None,
        json: Any = None,
    ) -> ClientResponse:
        r"""Send a POST request to the given endpoint.

        Args:
            endpoint: API endpoint (relative or absolute)
            params: parameters to be sent
            data: Data to send
            json: Alternative to data

        Returns:
            :class:`ClientResponse` object
        """
        url = urllib.parse.urljoin(self.base_url, endpoint.lstrip("/"))
        LOG.debug("POST url: %s", url)
        return await self.session.post(
            url, raise_for_status=True, params=params, data=data, json=json
        )
