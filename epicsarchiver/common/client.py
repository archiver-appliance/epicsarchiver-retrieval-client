"""Synchronous and asynchronous http clients for the archiver appliance."""

from __future__ import annotations

import contextlib
import logging
import urllib.parse
from typing import TYPE_CHECKING, Any

import httpx
from httpx import Response
from typing_extensions import Self

from epicsarchiver.common.errors import (
    ArchiverConnectionError,
    ArchiverResponseError,
)

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from types import TracebackType

LOG: logging.Logger = logging.getLogger(__name__)

DEFAULT_RETRIEVAL_PORT = 17668

DEFAULT_TIMEOUT = httpx.Timeout(60.0, connect=5.0)


class BaseClient:
    """Url handling and error translation shared by the sync and async clients.

    Args:
        base_url: base url of the service.
        timeout: timeout applied to every request
    """

    def __init__(
        self,
        base_url: str,
        timeout: httpx.Timeout | float | None = DEFAULT_TIMEOUT,
    ) -> None:
        """Create the client.

        Args:
            base_url: base url of the service.
            timeout (httpx.Timeout | float | None, optional): timeout applied to
                every request. Set to None to disable timeouts.
        """
        self.base_url = base_url
        self._timeout = timeout

    def __repr__(self) -> str:
        """String representation of the client.

        Returns:
            str: details including the base url of the service.
        """
        return f"{type(self).__name__}({self.base_url})"

    def _url(self, endpoint: str) -> str:
        """Resolve an endpoint against the base url.

        Args:
            endpoint: API endpoint (relative or absolute)

        Returns:
            str: the absolute url to request.
        """
        return urllib.parse.urljoin(self.base_url, endpoint.lstrip("/"))

    @contextlib.contextmanager
    def _errors(self, url: str) -> Iterator[None]:
        """Translate httpx errors into archiver errors.

        Args:
            url: the url being requested.

        Yields:
            None: while the request is made.

        Raises:
            ArchiverConnectionError: If there is a connection error.
            ArchiverResponseError: If the response is not successful.
        """
        try:
            yield
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


class BaseArchiverAppliance(BaseClient):
    """Base EPICS Archiver Appliance client.

    Hold a session to the Archiver Appliance web application.

    Args:
        base_url: base url of the Archiver Appliance
        timeout: timeout applied to every request
    """

    def __init__(
        self,
        base_url: str,
        timeout: httpx.Timeout | float | None = DEFAULT_TIMEOUT,
    ) -> None:
        """Create Archiver Appliance object.

        Args:
            base_url: base url of the Archiver Appliance.
            timeout (httpx.Timeout | float | None, optional): timeout applied to
                every request. Set to None to disable timeouts.
        """
        super().__init__(base_url, timeout)
        self._session: httpx.Client | None = None

    @property
    def session(self) -> httpx.Client:
        """Return the httpx client.

        Returns:
            httpx.Client: The session.
        """
        if not self._session:
            self._session = httpx.Client(timeout=self._timeout, follow_redirects=True)
        return self._session

    def close(self) -> None:
        """Close the client (closes the session)."""
        if self._session is not None:
            self._session.close()

    def __enter__(self) -> Self:
        """Enter the context manager.

        Returns:
            Self: self
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the context manager, closes the session."""
        self.close()

    def _get(self, endpoint: str, params: Mapping[str, str] | None = None) -> Response:
        """Send a GET request to the given endpoint.

        Args:
            endpoint: API endpoint (relative or absolute)
            params: query parameters to include in the request.

        Returns:
            :class:`httpx.Response <Response>` object
        """
        url = self._url(endpoint)
        LOG.debug("GET url: %s", url)
        with self._errors(url):
            response = self.session.get(url, params=params)
            response.raise_for_status()
        return response


class ServiceClient(BaseClient):
    """An async http service client.

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
        super().__init__(base_url, timeout)
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
        """
        url = self._url(endpoint)
        LOG.debug("GET url: %s", url)
        with self._errors(url):
            response = await self.session.get(url, params=params)
            response.raise_for_status()
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
        """
        url = self._url(endpoint)
        LOG.debug("POST url: %s", url)
        with self._errors(url):
            response = await self.session.post(url, params=params, data=data, json=json)
            response.raise_for_status()
        return response
