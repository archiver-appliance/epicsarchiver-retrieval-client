"""Minimal Channel Finder interface for calculating archiver statistics."""

import asyncio
import logging
from dataclasses import dataclass
from itertools import chain
from typing import Any

import urllib3
from universalasync import wrap

from epicsarchiver.service import ServiceClient

LOG: logging.Logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Channel:
    """Outline class of a channel finder channel data.

    Returns:
        Channel: includes name, properties and tags of a channel.
    """

    name: str
    properties: dict[str, str]
    tags: list[str]

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "Channel":
        """Convert from json direct from channel finder to a "Channel".

        Args:
            json (dict): input json dictionary

        Returns:
            Channel: corresponding channel
        """
        return Channel(
            json["name"],
            {p["name"]: p["value"] for p in json["properties"]},
            [t["name"] for t in json["tags"]],
        )

    def __hash__(self) -> int:
        """Calculates a has of a "Channel".

        Returns:
            int: hash of channel
        """
        return hash(
            self.name + str(tuple(sorted(self.properties.items()))) + str(self.tags),
        )


@dataclass
class ChannelFinderRequestError(BaseException):
    """Exception raised when error running requests against the channelfinder."""

    url: str
    params: dict[str, str]
    session_info: str


@wrap
class ChannelFinder(ServiceClient):
    """Minimal Channel Finder client.

    Hold a session to the Channel Finder web application.

    Args:
        hostname: Channel Finder url [default: localhost]

    Examples:

    .. code-block:: python

        from epicsarchiver.channelfinder import ChannelFinder

        channelfinder = ChannelFinder("channelfinder.tn.esss.lu.se")
        channel = channelfinder.get_channels(["AccPSS::FBIS-BP_A"])
    """

    def __init__(self, hostname: str = "localhost"):
        """Create Channel Finder object.

        Args:
            hostname (str, optional): hostname of channelfinder.
        """
        self.hostname = hostname
        super().__init__(f"https://{hostname}")

    async def _fetch_channels(
        self,
        url: str,
        params: dict[str, str],
    ) -> list[Channel]:
        async with await self._get(url, params=params) as value:
            value_json = await value.json()
            LOG.debug("Result from channelfinder search: %s", str(value_json))
            return [Channel.from_json(rs) for rs in value_json]

    def __repr__(self) -> str:
        """String representation of Channel Finder.

        Returns:
            str: details including hostname of Channel Finder.
        """
        return f"ChannelFinder({self.hostname})"

    async def get_channels(
        self,
        pvs: list[str] | None,
        alias: str | None = None,
        ioc_name: str | None = None,
    ) -> list[Channel]:
        """Get the list of channels matching the pv name from channelfinder.

        Args:
            session (aiohttp.ClientSession | None): aiohttp shared session
            pvs (list[str]): pv names
            alias (str): alias for a pv
            ioc_name (str): ioc name to filter by

        Returns:
            list[Channel]: list of matching channels
        """
        url = "/ChannelFinder/resources/channels"
        urllib3.disable_warnings()  # ignoring warnings that certificate is self signed
        params = {}
        if pvs and len(pvs) > 0:
            params["~name"] = ",".join(pvs)
        if alias:
            params["alias"] = alias
        if ioc_name:
            params["iocName"] = ioc_name
        LOG.debug("GET url: %s params: %s", url, str(params))
        return await self._fetch_channels(url, params=params)

    async def get_all_channels(
        self, pvs: list[str], group_size: int = 10
    ) -> dict[str, Channel]:
        """Get the list of channels matching the pv names from channelfinder.

        Args:
            pvs (list[str]): list of pv names
            group_size (int): Number of pvs to search at once to submit to channelfinder

        Returns:
            dict[str, Channel]: dict of matching channels
        """
        pv_groups = [pvs[i : i + group_size] for i in range(0, len(pvs), group_size)]
        LOG.debug(pv_groups)
        channel_request_res: list[list[Channel]] = await asyncio.gather(*[
            self.get_channels(pv_group) for pv_group in pv_groups
        ])
        channels: set[Channel] = set(chain(*channel_request_res))

        pvs_set = set(pvs)
        return {
            channel.name: channel for channel in channels if channel.name in pvs_set
        }

    async def get_ioc_channels(self, ioc_name: str) -> list[Channel]:
        """Get the list of channels with the specified ioc_name.

        Args:
            ioc_name: name of the ioc

        Returns:
            dict[str, Channel]: dict of matching channels
        """
        return await self.get_channels(None, ioc_name=ioc_name)

    async def get_all_alias_channels(
        self,
        pvs: list[str],
        ioc_name: str | None = None,
    ) -> dict[str, list[Channel]]:
        """Get the list of channels aliases of pvs from channelfinder.

        Args:
            pvs (list[str]): list of pv names
            ioc_name (str): ioc to filter by

        Returns:
            dict[str, list[Channel]]: dict of matching channels to pv names
        """
        alias_channel_requests = await asyncio.gather(*[
            self.get_channels([], alias=pv, ioc_name=ioc_name) for pv in pvs
        ])
        channels = set(chain(*alias_channel_requests))

        pvs_set = set(pvs)
        return {
            pv: [channel for channel in channels if channel.properties["alias"] == pv]
            for pv in pvs_set
        }
