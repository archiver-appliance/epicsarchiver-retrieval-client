from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from numpy import mean

from epicsarchiver.statistics.stat_responses import (
    UNKNOWN_IOC,
    BothArchiversResponse,
    Ioc,
    NameCheckResponse,
)

if TYPE_CHECKING:
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


INVALID_SUFFIXES = [
    "ACCESS",
    "Access",
    "BaseVersion",
    "EPICS_VERS",
    "EPICS_VERSION",
    "GTIM_CUR_SRC",
    "GTIM_ERR_CNT",
    "GTIM_EVT_SRC",
    "GTIM_HI_SRC",
    "GTIM_RESET",
    "GTIM_TIME",
    "GenTimeErrCount",
    "GenTimeErrReset",
    "GenTimeEventProvider",
    "GenTimeHighestProvider",
    "GenTimeSource",
    "GenTimeTime",
    "HEARTBEAT",
    "HOSTNAME",
    "Heartbeat",
    "Hostname",
    "IOCVERSION",
    "LOAD",
    "LOCATION",
    "Labels",
    "ModuleVersions",
    "Modules",
    "PARENT_ID",
    "PID",
    "PROCESS_ID",
    "ParentPID",
    "READACF",
    "ReadACF",
    "RecSync-Msg-I",
    "RecSync-State-Sts",
    "START_CNT",
    "ST_SCRIPT",
    "ST_SCRIPT1",
    "ST_SCRIPT2",
    "SYSRESET",
    "StartCount",
    "StartupScript",
    "UPTIME",
    "Uptime",
    "Versions",
    "as-AutosaveStatus",
    "as-DeadIfZero",
    "as-Disable",
    "as-DisableMaxSeconds",
    "as-Heartbeat",
    "as-MostRecentStatus",
    "as-Pass0-Method",
    "as-Pass0-Name",
    "as-Pass0-Status",
    "as-Pass0-Status-Msg",
    "as-Pass0-Time",
    "as-Pass1-Name",
    "as-Pass1-State",
    "as-Pass1-Status",
    "as-Pass1-Status-Msg",
    "as-Pass1-Time",
    "as-RebootStatus",
    "as-RebootStatus-Msg",
    "as-RebootTime",
    "as-SR_0_Name",
    "as-SR_0_State",
    "as-SR_0_Status",
    "as-SR_0_StatusStr",
    "as-SR_0_Time",
    "as-SR_1_Name",
    "as-SR_1_State",
    "as-SR_1_Status",
    "as-SR_1_StatusStr",
    "as-SR_1_Time",
    "as-SR_2_Name",
    "as-SR_2_State",
    "as-SR_2_Status",
    "as-SR_2_StatusStr",
    "as-SR_2_Time",
    "as-SR_3_Name",
    "as-SR_3_State",
    "as-SR_3_Status",
    "as-SR_3_StatusStr",
    "as-SR_3_Time",
    "as-SR_4_Name",
    "as-SR_4_State",
    "as-SR_4_Status",
    "as-SR_4_StatusStr",
    "as-SR_4_Time",
    "as-SR_5_Name",
    "as-SR_5_State",
    "as-SR_5_Status",
    "as-SR_5_StatusStr",
    "as-SR_5_Time",
    "as-SR_6_Name",
    "as-SR_6_State",
    "as-SR_6_Status",
    "as-SR_6_StatusStr",
    "as-SR_6_Time",
    "as-SR_7_Name",
    "as-SR_7_State",
    "as-SR_7_Status",
    "as-SR_7_StatusStr",
    "as-SR_7_Time",
    "as-SR_deadIfZero",
    "as-SR_disable",
    "as-SR_disableMaxSecs",
    "as-SR_heartbeat",
    "as-SR_i_am_alive",
    "as-SR_rebootStatus",
    "as-SR_rebootStatusStr",
    "as-SR_rebootTime",
    "as-SR_recentlyStr",
    "as-SR_status",
    "as-SR_statusStr",
    "as-Trigger",
    "as-WorstCaseStatus",
    "autosaveVersion",
    "caputlogVersion",
    "essiocVersion",
    "iocstatsVersion",
    "recsyncVersion",
    "requireVersion",
]


def _check_suffix_match(pv: str) -> str | None:
    if any(pv.endswith(suffix_match := suffix) for suffix in INVALID_SUFFIXES):
        return suffix_match
    return None


def _check_internal(pv: str) -> bool:
    return "#" in pv


def _check_names(
    pvs: set[str],
) -> list[NameCheckResponse]:
    output = []
    for pv in pvs:
        if _check_internal(pv):
            output.append(NameCheckResponse(pv, None, True))  # noqa: FBT003
        if suffix_match := _check_suffix_match(pv):
            output.append(NameCheckResponse(pv, suffix_match, False))  # noqa: FBT003
    return output


async def get_invalid_names(archiver: ArchiverWrapper) -> list[NameCheckResponse]:
    """Checks a list of pvs has an invalid suffix or is internal (contains #).

    Args:
        archiver (ArchiverWrapper): Archiver to check

    Returns:
        list[NameCheckResponse]: Response to check
    """
    all_non_paused_pvs = await get_all_non_paused_pvs(archiver)
    return _check_names(all_non_paused_pvs)
