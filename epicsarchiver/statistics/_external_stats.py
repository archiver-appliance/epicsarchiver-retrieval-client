from __future__ import annotations

import asyncio
import logging
from os import listdir
from typing import TYPE_CHECKING

from numpy import mean

from epicsarchiver.mgmt.archive_files import get_pvs_from_files
from epicsarchiver.statistics.gitlab import Gitlab
from epicsarchiver.statistics.stat_responses import (
    UNKNOWN_IOC,
    BothArchiversResponse,
    ConfiguredStatus,
    Ioc,
    NoConfigResponse,
)

if TYPE_CHECKING:
    from pathlib import Path

    from epicsarchiver.statistics.archiver_statistics import ArchiverWrapper
    from epicsarchiver.statistics.channelfinder import ChannelFinder

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


async def fetch_configured_pvs(config_gitlab_repo: Path) -> set[str]:
    gitlab = Gitlab()
    config_files = await gitlab.get_tar_ball(config_gitlab_repo)
    await gitlab.close()
    onlyfiles = [
        config_files / f
        for f in listdir(config_files)
        if (config_files / f).is_file() and f.endswith(".archive")
    ]
    return {ar["pv"] for ar in get_pvs_from_files(onlyfiles)}


async def get_not_configured(
    archiver: ArchiverWrapper,
    channelfinder: ChannelFinder,
    config_gitlab_repo: Path,
    ioc_name: str | None = None,
    filter_pvs: set[str] | None = None,
) -> list[NoConfigResponse]:
    """Return list of pvs archived but not in config or configured but not archived.

    Args:
        archiver (ArchiverAppliance): archiver
        channelfinder (ChannelFinder): channelfinder
        config_gitlab_repo (Path): Gitlab repo with files with lists of pvs
        ioc_name (str): Name of an ioc to filter by
        filter_pvs (set[str]): Set of pvs to filter by

    Returns:
        list[NoConfigResponse]: Details of pvs.
    """
    file_pvs = await fetch_configured_pvs(config_gitlab_repo)
    all_pvs = set(archiver.mgmt.get_all_pvs(limit=-1))
    all_non_paused_pvs = await get_all_non_paused_pvs(archiver, all_pvs=all_pvs)

    if filter_pvs:
        file_pvs = filter_pvs.intersection(file_pvs)
        all_pvs = filter_pvs.intersection(all_pvs)
        all_non_paused_pvs = filter_pvs.intersection(all_non_paused_pvs)

    archived_not_configured = set(all_non_paused_pvs - file_pvs)
    LOG.info("%s Archived but not configured.", len(archived_not_configured))
    configured_not_archived = set(file_pvs - all_pvs)
    LOG.info("%s Configured but not archived.", len(configured_not_archived))

    responses = await asyncio.gather(*[
        _get_configuration_responses(
            channelfinder,
            all_pvs,
            archived_not_configured,
            ConfiguredStatus.Archived,
            ioc_name,
        ),
        _get_configuration_responses(
            channelfinder,
            all_pvs,
            configured_not_archived,
            ConfiguredStatus.Configured,
            ioc_name,
        ),
    ])
    return list(responses[0] + responses[1])


async def _get_configuration_responses(
    channelfinder: ChannelFinder,
    all_pvs: set[str],
    pvs: set[str],
    status: ConfiguredStatus,
    ioc_name: str | None = None,
) -> list[NoConfigResponse]:
    aliases = await get_aliases(channelfinder, list(pvs), ioc_name=ioc_name)

    return [
        NoConfigResponse(
            pv,
            status,
            aliases[pv],
            [pv_alias for pv_alias in aliases[pv] if pv_alias in all_pvs],
        )
        for pv in pvs
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
    channels = await channelfinder.get_all_channels(
        pvs,
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


async def get_aliases(
    channelfinder: ChannelFinder,
    pvs: list[str],
    ioc_name: str | None,
) -> dict[str, list[str]]:
    """Get the aliases for a list of pvs.

    Args:
        channelfinder (ChannelFinder): channelfinder
        pvs (list[str]): list of pv names
        ioc_name (str): ioc to filter by

    Returns:
        dict[str, list[str]]: dictionary mapping pv name to list of aliases
    """
    channels = await channelfinder.get_all_alias_channels(pvs, ioc_name=ioc_name)
    return {pv: [channel.name for channel in channels[pv]] for pv in channels}
