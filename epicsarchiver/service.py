"""Module to cover the ServiceClient for doing http calls."""

import logging
import urllib.parse
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from aiohttp import ClientResponse, ClientSession
from universalasync import get_event_loop, wrap

if TYPE_CHECKING:
    import asyncio

LOG: logging.Logger = logging.getLogger(__name__)


@wrap
class ServiceClient:
    """An async and sync http service client.

    For doing basic GET POST http calls.
    """

    def __init__(self, base_url: str) -> None:
        """Create Service object."""
        self.base_url = base_url
        self._sessions: dict[asyncio.AbstractEventLoop, ClientSession] = {}

    @property
    def session(self) -> ClientSession:
        """Get a client session to send requests with.

        Returns:
            ClientSession: An asynchronous session.
        """
        loop = get_event_loop()
        session = self._sessions.get(loop)
        if session is not None:
            return session
        self._sessions[loop] = ClientSession()
        return self._sessions[loop]

    async def _close(self) -> None:
        for session in self._sessions.values():
            if session is not None:
                await session.close()

    def __del__(self) -> None:
        """Delete method makes sure to close any clients first."""
        loop = get_event_loop()
        if loop.is_running():
            loop.create_task(self._close())
        else:
            loop.run_until_complete(self._close())

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
        return await self.session.get(url, params=params, raise_for_status=True)

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
