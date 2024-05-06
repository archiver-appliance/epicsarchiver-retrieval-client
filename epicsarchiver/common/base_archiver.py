"""Base Archiver Client module for get, post etc requests."""

from __future__ import annotations

import logging
import urllib.parse
from typing import Any

import requests
from requests import Response

LOG: logging.Logger = logging.getLogger(__name__)


def mgmt_url(hostname: str, port: int) -> str:
    """Generate the mgmt url from a hostname and a port number.

    Args:
        hostname (str): fqdn of service
        port (int): Port number

    Returns:
        str: Completed url, for example "http://localhost:17665/mgmt/bpl/"
    """
    return f"http://{hostname}:{port}/mgmt/bpl/"


class BaseArchiverAppliance:
    """Base EPICS Archiver Appliance client.

    Hold a session to the Archiver Appliance web application.

    Args:
        hostname: EPICS Archiver Appliance hostname [default: localhost]
        port: EPICS Archiver Appliance management port [default: 17665]
    """

    def __init__(self, hostname: str = "localhost", port: int = 17665):
        """Create Archiver Appliance object.

        Args:
            hostname (str, optional): hostname of archiver. Defaults to "localhost".
            port (int, optional): port number of mgmt interface. Defaults to 17665.
        """
        self.hostname = hostname
        self.port = port
        self.mgmt_url = mgmt_url(hostname, port)
        self._info: dict[str, str] = {}
        self._data_url: str | None = None
        self.session = requests.Session()

    def __repr__(self) -> str:
        """String representation of Archiver Appliance.

        Returns:
            str: details including hostname of Archiver appliance.
        """
        return f"ArchiverAppliance({self.hostname}, {self.port})"

    def _request(self, method: str, *args: Any, **kwargs: Any) -> Response:
        r"""Sends a request using the session.

        Args:
            method: HTTP method
            *args: Optional arguments
            **kwargs: Optional keyword arguments

        Returns:
            :class:`requests.Response <Response>` object
        """
        r = self.session.request(method, *args, **kwargs)
        r.raise_for_status()
        return r

    def _get(self, endpoint: str, **kwargs: Any) -> Response:
        r"""Send a GET request to the given endpoint.

        Args:
            endpoint: API endpoint (relative or absolute)
            **kwargs: Optional arguments to be sent

        Returns:
            :class:`requests.Response <Response>` object
        """
        url = urllib.parse.urljoin(self.mgmt_url, endpoint.lstrip("/"))
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
        url = urllib.parse.urljoin(self.mgmt_url, endpoint.lstrip("/"))
        return self._request("POST", url, **kwargs)

    @property
    def info(self) -> dict[str, str]:
        """EPICS Archiver Appliance information."""
        if not self._info:
            # http://slacmshankar.github.io/epicsarchiver_docs/api/org/epics/archiverappliance/mgmt/bpl/GetApplianceInfo.html
            r = self._get("/getApplianceInfo")
            self._info = r.json()
        return self._info

    @property
    def identity(self) -> str | None:
        """EPICS Archiver Appliance identity."""
        return self.info.get("identity")

    @property
    def version(self) -> str | None:
        """EPICS Archiver Appliance version."""
        return self.info.get("version")

    def _get_or_post(self, endpoint: str, pv: str) -> Any:
        """Send a GET or POST if pv is a comma separated list.

        Args:
            endpoint: API endpoint
            pv: name of the pv. Can be a GLOB wildcards or a list of
                comma separated names.

        Returns:
            list of submitted PVs
        """
        r = (
            self._post(endpoint, data=pv)
            if "," in pv
            else self._get(endpoint, params={"pv": pv})
        )
        return r.json()
