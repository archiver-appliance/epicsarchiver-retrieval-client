"""Base Archiver Client module for get, post etc requests."""

from __future__ import annotations

import logging
import urllib.parse

import requests
from requests import Response

from epicsarchiver.common.errors import (
    ArchiverConnectionError,
    ArchiverResponseError,
)

LOG: logging.Logger = logging.getLogger(__name__)

DEFAULT_RETRIEVAL_PORT = 17668


class BaseArchiverAppliance:
    """Base EPICS Archiver Appliance client.

    Hold a session to the Archiver Appliance web application.

    Args:
        hostname: EPICS Archiver Appliance hostname
        port: EPICS Archiver Appliance retrieval port
    """

    def __init__(self, hostname: str = "localhost", port: int = DEFAULT_RETRIEVAL_PORT):
        """Create Archiver Appliance object.

        Args:
            hostname (str, optional): hostname of archiver.
            port (int, optional): port number of mgmt interface.
        """
        self.hostname = hostname
        self.port = port
        self._base_url: str = f"http://{hostname}:{port}"
        self.session = requests.Session()

    def __repr__(self) -> str:
        """String representation of Archiver Appliance.

        Returns:
            str: details including hostname of Archiver appliance.
        """
        return f"ArchiverAppliance({self.hostname}, {self.port})"

    def _get(self, endpoint: str, params: dict[str, str]) -> Response:
        """Sends a request using the session.

        Args:
            endpoint: API endpoint (relative or absolute)
            params: query parameters to include in the request.

        Returns:
            :class:`requests.Response <Response>` object

        Raises:
            ArchiverConnectionError: If there is a connection error.
            ArchiverResponseError: If the response is not successful.
        """
        url = urllib.parse.urljoin(self._base_url, endpoint.lstrip("/"))
        LOG.debug("GET url: %s", url)
        try:
            r = self.session.get(url, params=params, stream=True)
            r.raise_for_status()
        except requests.ConnectionError as e:
            raise ArchiverConnectionError(
                base_url=url,
            ) from e
        except requests.HTTPError as e:
            raise ArchiverResponseError(
                base_url=url,
                url=url,
                response=e.response.text if e.response else None,
            ) from e
        else:
            return r
