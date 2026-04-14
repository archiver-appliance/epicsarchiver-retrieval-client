"""Base Archiver Client module for get, post etc requests."""

from __future__ import annotations

import logging
import urllib.parse
from typing import Any

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

    def _request(self, method: str, url: str, **kwargs: Any) -> Response:
        """Sends a request using the session.

        Args:
            method: HTTP method
            url: The URL to send the request to
            **kwargs: Optional keyword arguments

        Returns:
            :class:`requests.Response <Response>` object

        Raises:
            ArchiverConnectionError: If there is a connection error.
            ArchiverResponseError: If the response is not successful.
        """
        try:
            r = self.session.request(method, url, **kwargs)
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

    def _get(self, endpoint: str, **kwargs: Any) -> Response:
        r"""Send a GET request to the given endpoint.

        Args:
            endpoint: API endpoint (relative or absolute)
            **kwargs: Optional arguments to be sent

        Returns:
            :class:`requests.Response <Response>` object
        """
        url = urllib.parse.urljoin(self._base_url, endpoint.lstrip("/"))
        LOG.debug("GET url: %s", url)
        return self._request("GET", url, **kwargs)

    def _post(self, endpoint: str, **kwargs: Any) -> Response:
        r"""Send a POST request to the given endpoint.

        Args:
            endpoint: API endpoint (relative or absolute)
            **kwargs: Optional arguments to be sent

        Returns:
            :class:`requests.Response <Response>` object
        """
        url = urllib.parse.urljoin(self._base_url, endpoint.lstrip("/"))
        return self._request("POST", url, **kwargs)

    def _get_or_post(self, endpoint: str, pv: str) -> Any:
        """Send a GET or POST if pv is a comma separated list.

        Args:
            endpoint (str): API endpoint
            pv (str): name of the pv. Can be a GLOB wildcards or a list of
                comma separated names.

        Returns:
            Any: list of submitted PVs
        """
        r = (
            self._post(endpoint, data=pv)
            if "," in pv
            else self._get(endpoint, params={"pv": pv})
        )
        return r.json()
