"""Minimal Channel Finder interface for calculating archiver statistics."""
import asyncio
import logging
import urllib.parse
from dataclasses import dataclass
from itertools import chain
from typing import Any

import aiohttp
import urllib3

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
            self.name + str(tuple(sorted(self.properties.items()))) + str(self.tags)
        )


@dataclass
class ChannelFinderRequestError(BaseException):
    """Exception raised when error running requests against the channelfinder."""

    url: str
    params: dict[str, str]
    session_info: str


class ChannelFinder:
    """Minimal Channel Finder client.

    Hold a session to the Channel Finder web application.

    Args:
        hostname: Channel Finder url [default: localhost]

    Basic Usage::

        >>> from epicsarchiver.channelfinder import ChannelFinder
        >>> channelfinder = ChannelFinder('channelfinder.tn.esss.lu.se')
        >>> channel = channelfinder.get_channels(['AccPSS::FBIS-BP_A'])
    """

    def __init__(self, hostname: str = "localhost"):
        """Create Channel Finder object.

        Args:
            hostname (str, optional): hostname of channelfinder.
        """
        self.hostname = hostname

    def __repr__(self) -> str:
        """String representation of Channel Finder.

        Returns:
            str: details including hostname of Channel Finder.
        """
        return f"ChannelFinder({self.hostname})"

    async def get_channels(
        self,
        session: aiohttp.ClientSession | None,
        pvs: list[str],
        alias: str | None = None,
    ) -> list[Channel]:
        """Get the list of channels matching the pv name from channelfinder.

        Args:
            session (aiohttp.ClientSession | None): aiohttp shared session
            pvs (list[str]): pv names
            alias (str): alias for a pv
            max_size (int): max number of returned channels, default 50 000

        Returns:
            list[Channel]: list of matching channels
        """
        url = urllib.parse.urljoin(
            f"https://{self.hostname}", "/ChannelFinder/resources/channels"
        )
        urllib3.disable_warnings()  # ignoring warnings that certificate is self signed
        params = {}
        if len(pvs) > 0:
            params["~name"] = ",".join(pvs)
        if alias:
            params["alias"] = alias
        LOG.debug("GET url: " + url + " params: " + str(params))
        if not session:
            async with aiohttp.ClientSession() as session:
                return await self._fetch(session, url, params)
        else:
            return await self._fetch(session, url, params)

    async def _fetch(
        self,
        session: aiohttp.ClientSession,
        url: str,
        params: dict[str, str],
    ) -> list[Channel]:
        async with session.get(
            url=url, params=params, raise_for_status=True, ssl=False
        ) as value:
            value_json = await value.json()
            LOG.debug("Result from channelfinder search: " + str(value_json))
            return [Channel.from_json(rs) for rs in value_json]

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
        async with aiohttp.ClientSession() as session:
            channel_request_res: list[list[Channel]] = await asyncio.gather(
                *[self.get_channels(session, pv_group) for pv_group in pv_groups]
            )
            channels: set[Channel] = set(chain(*channel_request_res))

            pvs_set = set(pvs)
            channels_dict = {
                channel.name: channel for channel in channels if channel.name in pvs_set
            }
            return channels_dict

    async def get_all_alias_channels(
        self,
        pvs: list[str],
    ) -> dict[str, list[Channel]]:
        """Get the list of channels aliases of pvs from channelfinder.

        Args:
            pvs (list[str]): list of pv names

        Returns:
            dict[str, list[Channel]]: dict of matching channels to pv names
        """
        async with aiohttp.ClientSession() as session:
            alias_channel_requests = await asyncio.gather(
                *[self.get_channels(session, [], alias=pv) for pv in pvs]
            )
            channels = set(chain(*alias_channel_requests))

            pvs_set = set(pvs)
            channels_dict = {
                pv: [
                    channel for channel in channels if channel.properties["alias"] == pv
                ]
                for pv in pvs_set
            }
            return channels_dict
