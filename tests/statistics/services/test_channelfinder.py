import json
import logging

import pytest
from aioresponses import aioresponses
from rich.logging import RichHandler

from epicsarchiver.statistics.services.channelfinder import (
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
            },
        ]
        mocked.get(url, body=json.dumps(data))
        async with ChannelFinder() as channelfinder:
            r = await channelfinder.get_channels({"fred"})
            assert len(r) == 1
            expected_channel = Channel(
                "fred",
                {
                    "hostName": "host.blah",
                    "iocName": "FredsIOC",
                    "pvStatus": "Inactive",
                },
                [],
            )
            assert r[0] == expected_channel


@pytest.mark.asyncio
async def test_get_ioc_channels() -> None:
    with aioresponses() as mocked:
        url = "https://localhost/ChannelFinder/resources/scroll/?iocName=iocName"
        data = {
            "id": None,
            "channels": [
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
                },
            ],
        }
        mocked.get(url, body=json.dumps(data))
        async with ChannelFinder() as channelfinder:
            r = await channelfinder.get_ioc_channels("iocName")
            assert len(r) == 1
            expected_channel = Channel(
                "fred",
                {
                    "hostName": "host.blah",
                    "iocName": "FredsIOC",
                    "pvStatus": "Inactive",
                },
                [],
            )
            assert r[0] == expected_channel


@pytest.mark.asyncio
async def test_get_all_channels() -> None:
    with aioresponses() as mocked:
        url1a = "https://localhost/ChannelFinder/resources/channels?~name=ac,ab"
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
        mocked.get(url1a, body=json.dumps(dataa))
        # Need to mock both because input list of pvs is a set so can be in many orders
        url1b = "https://localhost/ChannelFinder/resources/channels?~name=ab,ac"
        mocked.get(url1b, body=json.dumps(dataa))
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

        async with ChannelFinder() as channelfinder:
            r = await channelfinder.get_channels_chunked(
                ["ac", "ab", "ba"], chunk_size=2
            )
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


@pytest.mark.asyncio
async def test_get_channels_scroll() -> None:
    with aioresponses() as mocked:
        url1 = "https://localhost/ChannelFinder/resources/scroll/?prop=propValue"
        data1 = {
            "id": "A",
            "channels": [
                {
                    "name": "fred",
                    "owner": "recceiver",
                    "properties": [],
                    "tags": [],
                },
            ],
        }
        mocked.get(url1, body=json.dumps(data1))
        url2 = "https://localhost/ChannelFinder/resources/scroll/A?prop=propValue"
        data2 = {
            "id": None,
            "channels": [
                {
                    "name": "fred2",
                    "owner": "recceiver",
                    "properties": [],
                    "tags": [],
                },
            ],
        }
        mocked.get(url2, body=json.dumps(data2))
        async with ChannelFinder() as channelfinder:
            r = await channelfinder.get_channels(None, {"prop": "propValue"})
            assert len(r) == 2
            expected_channels = [
                Channel(
                    "fred",
                    {},
                    [],
                ),
                Channel(
                    "fred2",
                    {},
                    [],
                ),
            ]
            assert expected_channels == r
