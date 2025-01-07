"""Module for getting the PVs which have been requested to be submitted to the archiver.

Also calculates if a PV is being archived with no configuration left over, common when
a PV name has changed.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from attr import dataclass

from epicsarchiver.mgmt.archive_files import get_pvs_from_files
from epicsarchiver.statistics import _external_stats
from epicsarchiver.statistics.models.stat_responses import (
    ConfiguredStatus,
    NoConfigResponse,
)
from epicsarchiver.statistics.services.gitlab import Gitlab

if TYPE_CHECKING:
    from pathlib import Path

    from epicsarchiver.statistics.services.archiver_statistics import ArchiverWrapper
    from epicsarchiver.statistics.services.channelfinder import ChannelFinder

LOG: logging.Logger = logging.getLogger(__name__)

CHANNELFINDER_ARCHIVE_TAG = "aa_policy"
CHANNELFINDER_ARCHIVER_ALIAS = "archiver"


@dataclass
class ConfigOptions:
    """Options in how a PV can be configured.

    gitlab_repo: Repository where archive config files ly
    archiver_alias: Tag used in ChannelFinder to select an archiver cluster.
    """

    gitlab_repo: Path | None
    archiver_alias: str | None


async def _fetch_configured_pvs_channelfinder(
    channelfinder: ChannelFinder,
    archiver_alias: str,
    filter_pvs: set[str] | None = None,
) -> set[str]:
    return set(
        (
            await channelfinder.get_channels_chunked(
                list(filter_pvs) if filter_pvs else None,
                {
                    CHANNELFINDER_ARCHIVE_TAG: "*",
                    CHANNELFINDER_ARCHIVER_ALIAS: archiver_alias,
                },
            )
        ).keys()
    )


async def _fetch_configured_pvs_gitlab(config_gitlab_repo: Path) -> set[str]:
    gitlab = Gitlab()
    config_files = await gitlab.get_tar_ball(config_gitlab_repo)
    await gitlab.close()
    onlyfiles = [
        config_files / f
        for f in config_files.iterdir()
        if (config_files / f).is_file() and f.suffix == ".archive"
    ]
    return {ar["pv"] for ar in get_pvs_from_files(onlyfiles)}


async def get_not_configured(
    archiver: ArchiverWrapper,
    channelfinder: ChannelFinder,
    config_options: ConfigOptions,
    ioc_name: str | None = None,
    filter_pvs: set[str] | None = None,
) -> list[NoConfigResponse]:
    """Return list of pvs archived but not in config or configured but not archived.

    Args:
        archiver (ArchiverAppliance): archiver
        channelfinder (ChannelFinder): channelfinder
        config_options (ConfigOptions): Options on how submit PV to be archived
        ioc_name (str): Name of an ioc to filter by
        filter_pvs (set[str]): Set of pvs to filter by

    Returns:
        list[NoConfigResponse]: Details of pvs.
    """
    configured_pvs_gitlab = (
        await _fetch_configured_pvs_gitlab(config_options.gitlab_repo)
        if config_options.gitlab_repo
        else set()
    )
    configured_pvs_channelfinder = (
        await _fetch_configured_pvs_channelfinder(
            channelfinder, config_options.archiver_alias, filter_pvs=filter_pvs
        )
        if config_options.archiver_alias
        else set()
    )

    all_pvs = set(archiver.mgmt.get_all_pvs(limit=-1))
    all_non_paused_pvs = await _external_stats.get_all_non_paused_pvs(
        archiver, all_pvs=all_pvs
    )

    if filter_pvs:
        configured_pvs_gitlab = filter_pvs.intersection(configured_pvs_gitlab)
        all_pvs = filter_pvs.intersection(all_pvs)
        all_non_paused_pvs = filter_pvs.intersection(all_non_paused_pvs)

    archived_not_configured = set(
        all_non_paused_pvs - configured_pvs_gitlab - configured_pvs_channelfinder
    )

    LOG.info("%s Archived but not configured.", len(archived_not_configured))
    configured_not_archived = set(
        configured_pvs_channelfinder.union(configured_pvs_gitlab) - all_pvs
    )
    configured_gitlab_not_archived = configured_not_archived.intersection(
        configured_pvs_gitlab
    )
    LOG.info(
        "%s Configured Gitlab but not archived.", len(configured_gitlab_not_archived)
    )
    configured_channelfinder_not_archived = configured_not_archived.intersection(
        configured_pvs_channelfinder
    )
    LOG.info(
        "%s Configured ChannelFinder but not archived.",
        len(configured_channelfinder_not_archived),
    )

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
            configured_gitlab_not_archived,
            ConfiguredStatus.ConfiguredGitlab,
            ioc_name,
        ),
        _get_configuration_responses(
            channelfinder,
            all_pvs,
            configured_channelfinder_not_archived,
            ConfiguredStatus.ConfiguredChannelFinder,
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
