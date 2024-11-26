"""Minimal Channel Finder interface for calculating archiver statistics."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from itertools import chain
from typing import Any

import urllib3

from epicsarchiver.statistics.services.async_service import ServiceClient

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
    def from_json(cls, json: dict[str, Any]) -> Channel:
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


@dataclass(frozen=True)
class ScrollChannels:
    """Outline class of a channel finder channel data.

    Returns:
        Channel: includes name, properties and tags of a channel.
    """

    scroll_id: str | None
    channels: list[Channel]

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> ScrollChannels:
        """Convert from json direct from channel finder to a "Channel".

        Args:
            json (dict): input json dictionary

        Returns:
            Channel: corresponding channel
        """
        return ScrollChannels(
            json["id"],
            [
                Channel(
                    channel_json["name"],
                    {
                        property_json["name"]: property_json["value"]
                        for property_json in channel_json["properties"]
                    },
                    [tag_json["name"] for tag_json in channel_json["tags"]],
                )
                for channel_json in json["channels"]
            ],
        )


@dataclass
class ChannelFinderRequestError(BaseException):
    """Exception raised when error running requests against the channelfinder."""

    url: str
    params: dict[str, str]
    session_info: str


def _channel_list_to_dict(
    channels: list[Channel], pvs_set: set[str] | None
) -> dict[str, Channel]:
    return {
        channel.name: channel
        for channel in channels
        if pvs_set is None or channel.name in pvs_set
    }


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

    async def _fetch_channels_scroll(
        self,
        params: dict[str, str],
    ) -> list[Channel]:
        resource = "/ChannelFinder/resources/scroll"
        all_channels = []
        scroll_id = None
        while True:
            LOG.debug(
                "GET url: %s params: %s scroll_id: %s", resource, str(params), scroll_id
            )
            async with await self._get(
                f"{resource}/{scroll_id or ''}", params=params
            ) as value:
                value_json = await value.json()
                scroll_rs = ScrollChannels.from_json(value_json)
                all_channels += scroll_rs.channels
                if not scroll_rs.scroll_id:
                    break
                scroll_id = scroll_rs.scroll_id
        return all_channels

    async def _fetch_channels(
        self,
        params: dict[str, str],
    ) -> list[Channel]:
        resource = "/ChannelFinder/resources/channels"
        LOG.debug("GET url: %s params: %s", resource, str(params))
        async with await self._get(resource, params=params) as value:
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
        pvs: set[str] | None,
        properties: dict[str, str] | None = None,
    ) -> list[Channel]:
        """Get the list of channels matching the pv name from channelfinder.

        Args:
            pvs (list[str]): pv names
            properties (dict[str, str]): Properties to filter by

        Returns:
            list[Channel]: list of matching channels
        """
        urllib3.disable_warnings()  # ignoring warnings that certificate is self signed
        params = properties or {}
        if pvs and len(pvs) > 0:
            params["~name"] = ",".join(pvs)
        if not pvs:
            return await self._fetch_channels_scroll(params=params)
        return await self._fetch_channels(params=params)

    async def get_channels_chunked(
        self,
        pvs: list[str] | None,
        properties: dict[str, str] | None = None,
        chunk_size: int = 10,
    ) -> dict[str, Channel]:
        """Get the list of channels matching the pv names from channelfinder.

        Args:
            pvs (list[str]): list of pv names
            properties (dict[str, str]): Properties to filter by
            chunk_size (int): Number of pvs to search at once to submit to channelfinder

        Returns:
            dict[str, Channel]: dict of matching channels
        """
        if not pvs:
            return _channel_list_to_dict(
                await self.get_channels(None, properties=properties), None
            )
        pv_groups = [
            set(pvs[i : i + chunk_size]) for i in range(0, len(pvs), chunk_size)
        ]
        LOG.debug(pv_groups)
        channel_request_res: list[list[Channel]] = await asyncio.gather(*[
            self.get_channels(pv_group, properties=properties) for pv_group in pv_groups
        ])
        channels: set[Channel] = set(chain(*channel_request_res))

        pvs_set = set(pvs)
        return _channel_list_to_dict(list(channels), pvs_set)

    async def get_ioc_channels(self, ioc_name: str) -> list[Channel]:
        """Get the list of channels with the specified ioc_name.

        Args:
            ioc_name: name of the ioc

        Returns:
            dict[str, Channel]: dict of matching channels
        """
        return await self.get_channels(None, properties={"iocName": ioc_name})

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
            self.get_channels(
                set(),
                properties=(
                    {"alias": pv, "iocName": ioc_name} if ioc_name else {"alias": pv}
                ),
            )
            for pv in pvs
        ])
        channels = set(chain(*alias_channel_requests))

        pvs_set = set(pvs)
        return {
            pv: [channel for channel in channels if channel.properties["alias"] == pv]
            for pv in pvs_set
        }
