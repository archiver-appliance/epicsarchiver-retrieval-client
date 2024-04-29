import asyncio
import logging
from os import listdir
from pathlib import Path

from numpy import mean

from epicsarchiver.epicsarchiver import ArchiverAppliance
from epicsarchiver.mgmt.archive_files import get_pvs_from_files
from epicsarchiver.statistics.channelfinder import ChannelFinder
from epicsarchiver.statistics.gitlab import Gitlab
from epicsarchiver.statistics.stat_responses import (
    UNKNOWN_IOC,
    BothArchiversResponse,
    ConfiguredStatus,
    Ioc,
    NoConfigResponse,
)

LOG: logging.Logger = logging.getLogger(__name__)


async def get_all_non_paused_pvs(
    archiver: ArchiverAppliance,
    all_pvs: set[str] | None = None,
) -> set[str]:
    if not all_pvs:
        all_pvs = set(archiver.get_all_pvs(limit=-1))
    return set(all_pvs - {paused.pv_name for paused in archiver.get_paused_pvs()})


async def get_double_archived(
    archiver: ArchiverAppliance,
    other_archiver: ArchiverAppliance,
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
        BothArchiversResponse(pv, archiver.hostname, other_archiver.hostname)
        for pv in set(set(non_paused_pvs).intersection(set(other_non_paused_pvs)))
    ]


async def fetch_config_files(config_gitlab_repo: Path) -> Path:
    gitlab = Gitlab()
    return await gitlab.get_tar_ball(config_gitlab_repo)


async def get_not_configured(
    archiver: ArchiverAppliance,
    channelfinder: ChannelFinder | None,
    config_gitlab_repo: Path,
    ioc_name: str | None = None,
) -> list[NoConfigResponse]:
    """Return list of pvs archived but not in config or configured but not archived.

    Args:
        archiver (ArchiverAppliance): archiver
        channelfinder (ChannelFinder): channelfinder
        config_gitlab_repo (Path): Gitlab repo with files with lists of pvs
        ioc_name (str): Name of an ioc to filter by

    Returns:
        list[NoConfigResponse]: Details of pvs.
    """
    config_files = await fetch_config_files(config_gitlab_repo)
    onlyfiles = [
        config_files / f
        for f in listdir(config_files)
        if (config_files / f).is_file() and f.endswith(".archive")
    ]
    LOG.debug(
        "CALC Not configured PVs from %s and filed %s",
        archiver.hostname,
        onlyfiles,
    )
    all_pvs = set(archiver.get_all_pvs(limit=-1))
    all_non_paused_pvs = await get_all_non_paused_pvs(archiver, all_pvs=all_pvs)
    file_pvs = {ar["pv"] for ar in get_pvs_from_files(onlyfiles)}
    if not file_pvs:
        return []
    archived_not_configured = set(all_non_paused_pvs - file_pvs)
    LOG.info("%s Archived but not configured.", len(archived_not_configured))
    configured_not_archived = set(file_pvs - all_pvs)
    LOG.info("%s Configured but not archived.", len(configured_not_archived))
    if channelfinder:
        (
            archived_not_configured_alias,
            configured_not_archived_alias,
        ) = await asyncio.gather(*[
            get_aliases(
                channelfinder,
                list(archived_not_configured),
                ioc_name=ioc_name,
            ),
            get_aliases(
                channelfinder,
                list(configured_not_archived),
                ioc_name=ioc_name,
            ),
        ])

    responses = await asyncio.gather(*[
        _gen_no_config_responses(
            all_pvs,
            archived_not_configured,
            archived_not_configured_alias,
            ConfiguredStatus.Archived,
        ),
        _gen_no_config_responses(
            all_pvs,
            configured_not_archived,
            configured_not_archived_alias,
            ConfiguredStatus.Configured,
        ),
    ])
    return list(responses[0] + responses[1])


async def _gen_no_config_responses(
    all_archived_pvs: set[str],
    pv_list: set[str],
    aliases: dict[str, list[str]],
    configured_status: ConfiguredStatus,
) -> list[NoConfigResponse]:
    return [
        NoConfigResponse(
            pv,
            configured_status,
            aliases[pv],
            [pv_alias for pv_alias in aliases[pv] if pv_alias in all_archived_pvs],
        )
        for pv in pv_list
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
