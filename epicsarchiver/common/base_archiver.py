"""Base Archiver Client module for get, post etc requests."""

from __future__ import annotations

import logging
import urllib.parse
from typing import TYPE_CHECKING

import httpx
from httpx import Response

from epicsarchiver.common.errors import (
    ArchiverConnectionError,
    ArchiverResponseError,
)

if TYPE_CHECKING:
    from types import TracebackType

    from typing_extensions import Self

LOG: logging.Logger = logging.getLogger(__name__)

DEFAULT_RETRIEVAL_PORT = 17668

DEFAULT_TIMEOUT = httpx.Timeout(60.0, connect=5.0)


class BaseArchiverAppliance:
    """Base EPICS Archiver Appliance client.

    Hold a session to the Archiver Appliance web application.

    Args:
        hostname: EPICS Archiver Appliance hostname
        port: EPICS Archiver Appliance retrieval port
        timeout: timeout applied to every request
    """

    def __init__(
        self,
        hostname: str = "localhost",
        port: int = DEFAULT_RETRIEVAL_PORT,
        timeout: httpx.Timeout | float | None = DEFAULT_TIMEOUT,
    ):
        """Create Archiver Appliance object.

        Args:
            hostname (str, optional): hostname of archiver.
            port (int, optional): port number of retrieval interface.
            timeout (httpx.Timeout | float | None, optional): timeout applied to
                every request. Set to None to disable timeouts.
        """
        self.hostname = hostname
        self.port = port
        self._base_url: str = f"http://{hostname}:{port}"
        self.session = httpx.Client(timeout=timeout, follow_redirects=True)

    def __repr__(self) -> str:
        """String representation of Archiver Appliance.

        Returns:
            str: details including hostname of Archiver appliance.
        """
        return f"ArchiverAppliance({self.hostname}, {self.port})"

    def close(self) -> None:
        """Close the client (closes the session)."""
        self.session.close()

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

    def _get(self, endpoint: str, params: dict[str, str]) -> Response:
        """Sends a request using the session.

        Args:
            endpoint: API endpoint (relative or absolute)
            params: query parameters to include in the request.

        Returns:
            :class:`httpx.Response <Response>` object

        Raises:
            ArchiverConnectionError: If there is a connection error.
            ArchiverResponseError: If the response is not successful.
        """
        url = urllib.parse.urljoin(self._base_url, endpoint.lstrip("/"))
        LOG.debug("GET url: %s", url)
        try:
            r = self.session.get(url, params=params)
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ArchiverResponseError(
                base_url=url,
                url=url,
                response=e.response.text,
            ) from e
        except httpx.TransportError as e:
            raise ArchiverConnectionError(
                base_url=url,
            ) from e
        else:
            return r
