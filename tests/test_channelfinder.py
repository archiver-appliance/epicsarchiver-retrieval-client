import json
import logging

import pytest
from aioresponses import aioresponses
from rich.logging import RichHandler

from epicsarchiver.channelfinder import (
    Channel,
    ChannelFinder,
)

logging.basicConfig(
    level=logging.DEBUG,
    handlers=[RichHandler(rich_tracebacks=True)],
)
LOG: logging.Logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_get_channels() -> None:
    with aioresponses() as mocked:
        channelfinder = ChannelFinder()
        url = "https://localhost/ChannelFinder/resources/channels?~name=fred"
        data = [
            {
                "name": "fred",
                "owner": "recceiver",
                "properties": [
                    {
                        "name": "hostName",
                        "owner": "recceiver",
                        "value": "host.blah",
                        "channels": [],
                    },
                    {
                        "name": "iocName",
                        "owner": "recceiver",
                        "value": "FredsIOC",
                        "channels": [],
                    },
                    {
                        "name": "pvStatus",
                        "owner": "recceiver",
                        "value": "Inactive",
                        "channels": [],
                    },
                ],
                "tags": [],
            }
        ]
        mocked.get(url, body=json.dumps(data))
        r = await channelfinder.get_channels(None, ["fred"])
        assert len(r) == 1
        expected_channel = Channel(
            "fred",
            {"hostName": "host.blah", "iocName": "FredsIOC", "pvStatus": "Inactive"},
            [],
        )
        assert r[0] == expected_channel


@pytest.mark.asyncio
async def test_get_all_channels() -> None:
    with aioresponses() as mocked:
        channelfinder = ChannelFinder()
        urla = "https://localhost/ChannelFinder/resources/channels?~name=ac,ab"
        dataa = [
            {
                "name": "ab",
                "properties": [
                    {
                        "name": "hostName",
                        "value": "host.a",
                    },
                    {
                        "name": "iocName",
                        "value": "AIOC",
                    },
                ],
                "tags": [],
            },
            {
                "name": "ac",
                "properties": [
                    {
                        "name": "hostName",
                        "value": "host.a",
                    },
                    {
                        "name": "iocName",
                        "value": "AIOC",
                    },
                ],
                "tags": [],
            },
        ]
        mocked.get(urla, body=json.dumps(dataa))
        urlb = "https://localhost/ChannelFinder/resources/channels?~name=ba"
        datab = [
            {
                "name": "ba",
                "properties": [
                    {
                        "name": "hostName",
                        "value": "host.b",
                    },
                    {
                        "name": "iocName",
                        "value": "BIOC",
                    },
                ],
                "tags": [],
            },
        ]
        mocked.get(urlb, body=json.dumps(datab))
        r = await channelfinder.get_all_channels(["ac", "ab", "ba"], group_size=2)
        assert len(r) == 3
        expected_channels = {
            "ab": Channel(
                "ab",
                {"hostName": "host.a", "iocName": "AIOC"},
                [],
            ),
            "ac": Channel(
                "ac",
                {"hostName": "host.a", "iocName": "AIOC"},
                [],
            ),
            "ba": Channel(
                "ba",
                {"hostName": "host.b", "iocName": "BIOC"},
                [],
            ),
        }
        assert r == expected_channels
