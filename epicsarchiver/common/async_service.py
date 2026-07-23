"""Module to cover the ServiceClient for doing http calls."""

from __future__ import annotations

import logging
import urllib.parse
from typing import TYPE_CHECKING, Any

import httpx
from httpx import Response
from typing_extensions import Self

from epicsarchiver.common.base_archiver import DEFAULT_TIMEOUT
from epicsarchiver.common.errors import (
    ArchiverConnectionError,
    ArchiverResponseError,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from types import TracebackType

LOG: logging.Logger = logging.getLogger(__name__)


class ServiceClient:
    """An async and sync http service client.

    For doing basic GET POST http calls.
    """

    def __init__(
        self,
        base_url: str,
        timeout: httpx.Timeout | float | None = DEFAULT_TIMEOUT,
    ) -> None:
        """Create Service object.

        Args:
            base_url: base url of the service.
            timeout: timeout applied to every request. Set to None to disable
                timeouts.
        """
        self.base_url = base_url
        self._timeout = timeout
        self._session: httpx.AsyncClient | None = None

    @property
    def session(self) -> httpx.AsyncClient:
        """Return the httpx async client.

        Returns:
            httpx.AsyncClient: The session.
        """
        if not self._session:
            self._session = httpx.AsyncClient(
                timeout=self._timeout, follow_redirects=True
            )
        return self._session

    async def close(self) -> None:
        """Close the Service (closes the session)."""
        if self._session is not None:
            await self._session.aclose()

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
    ) -> Response:
        """Send a GET request to the given endpoint.

        Args:
            endpoint: API endpoint (relative or absolute)
            params: parameters to be sent

        Returns:
            :class:`httpx.Response <Response>` object

        Raises:
            ArchiverConnectionError: If there is a connection error.
            ArchiverResponseError: If the response is not successful.
        """
        url = urllib.parse.urljoin(self.base_url, endpoint.lstrip("/"))
        LOG.debug("GET url: %s", url)
        try:
            response = await self.session.get(url, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ArchiverResponseError(
                base_url=self.base_url,
                url=url,
                response=e.response.text or None,
            ) from e
        except httpx.TransportError as e:
            raise ArchiverConnectionError(
                base_url=self.base_url,
            ) from e
        else:
            return response

    async def _get_json(
        self, endpoint: str, params: Mapping[str, str] | None = None
    ) -> Any:
        """Send a GET request to the given endpoint and return the json.

        Args:
            endpoint: API endpoint (relative or absolute)
            params: parameters to be sent

        Returns:
            The decoded json body.
        """
        response = await self._get(endpoint, params=params)
        return response.json()

    async def _post(
        self,
        endpoint: str,
        params: Mapping[str, str] | None = None,
        data: Any = None,
        json: Any = None,
    ) -> Response:
        r"""Send a POST request to the given endpoint.

        Args:
            endpoint: API endpoint (relative or absolute)
            params: parameters to be sent
            data: Data to send
            json: Alternative to data

        Returns:
            :class:`httpx.Response <Response>` object

        Raises:
            ArchiverConnectionError: If there is a connection error.
            ArchiverResponseError: If the response is not successful.
        """
        url = urllib.parse.urljoin(self.base_url, endpoint.lstrip("/"))
        LOG.debug("POST url: %s", url)
        try:
            response = await self.session.post(url, params=params, data=data, json=json)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ArchiverResponseError(
                base_url=self.base_url,
                url=url,
                response=e.response.text or None,
            ) from e
        except httpx.TransportError as e:
            raise ArchiverConnectionError(
                base_url=self.base_url,
            ) from e
        else:
            return response
