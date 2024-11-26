from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from numpy import mean

from epicsarchiver.statistics.models.stat_responses import (
    UNKNOWN_IOC,
    BothArchiversResponse,
    Ioc,
)

if TYPE_CHECKING:
    from epicsarchiver.statistics.services.archiver_statistics import ArchiverWrapper
    from epicsarchiver.statistics.services.channelfinder import ChannelFinder

LOG: logging.Logger = logging.getLogger(__name__)


async def get_all_non_paused_pvs(
    archiver: ArchiverWrapper,
    all_pvs: set[str] | None = None,
) -> set[str]:
    all_archiver_pvs = all_pvs or set(archiver.mgmt.get_all_pvs(limit=-1))
    paused_pvs = {paused.pv_name for paused in await archiver.stats.get_paused_pvs()}
    return all_archiver_pvs - paused_pvs


async def get_double_archived(
    archiver: ArchiverWrapper,
    other_archiver: ArchiverWrapper,
) -> list[BothArchiversResponse]:
    """Return list of pvs archived in both archivers, filtered by those paused.

    Returns:
        list[BothArchiversResponse]: Details of pv and archivers.
    """
    non_paused_pvs, other_non_paused_pvs = await asyncio.gather(*[
        get_all_non_paused_pvs(archiver),
        get_all_non_paused_pvs(other_archiver),
    ])
    return [
        BothArchiversResponse(pv, archiver.mgmt.hostname, other_archiver.mgmt.hostname)
        for pv in set(set(non_paused_pvs).intersection(set(other_non_paused_pvs)))
    ]


async def get_iocs(
    channelfinder: ChannelFinder,
    pvs: list[str],
) -> dict[Ioc, list[str]]:
    """Get the IOC hosts for a list of pvs.

    Args:
        channelfinder (ChannelFinder): channelfinder
        pvs (list[str]): list of pv names

    Returns:
        dict[Ioc, list[str]]: dictionary mapping ioc name to pv
    """
    channels = await channelfinder.get_channels_chunked(
        pvs,
        None,
        int(mean([len(pv) for pv in pvs]) / 2),
    )
    iocs = {pv: Ioc.from_channel(channel) for pv, channel in channels.items()}

    for pv in pvs:
        if pv not in iocs:
            iocs[pv] = UNKNOWN_IOC

    output: dict[Ioc, list[str]] = {}
    for pv in pvs:
        if iocs[pv] not in output:
            output[iocs[pv]] = []
        output[iocs[pv]].append(pv)
    return output


async def filter_by_ioc(
    channelfinder: ChannelFinder,
    ioc_name: str,
    pvs: list[str],
) -> dict[Ioc, list[str]]:
    """Filter a list of pvs by an ioc name.

    Args:
        channelfinder (ChannelFinder): channelfinder
        ioc_name (str): ioc name
        pvs (list[str]): list of pv names

    Returns:
        dict[Ioc, list[str]]: dictionary mapping ioc name to pv
    """
    channels = await channelfinder.get_ioc_channels(ioc_name)
    if channels:
        return {
            Ioc.from_channel(channels[0]): [
                channel.name for channel in channels if channel.name in pvs
            ],
        }
    return {}
