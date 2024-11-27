"""PV Names module, methods for dealing with PV Names."""

from __future__ import annotations

import json
import logging
import operator
import re
from typing import TYPE_CHECKING

from epicsarchiver.statistics._external_stats import get_all_non_paused_pvs
from epicsarchiver.statistics.models.stat_responses import NameCheckResponse

if TYPE_CHECKING:
    from epicsarchiver.statistics.services.archiver_statistics import ArchiverWrapper

LOG: logging.Logger = logging.getLogger(__name__)


PV_NAME_REGEX = r"(?P<system>[a-zA-Z0-9\-]+):(?P<device>[a-zA-Z\-]+)\-[0-9a-zA-Z]+:*"
PV_NAME_PARTS = ["system", "device"]


def _get_pv_parts(pv: str) -> list[str]:
    regex_find = re.findall(PV_NAME_REGEX, pv)
    if len(regex_find) != 1:
        LOG.debug("pv %s does not match regex", pv)
        return []
    return list(regex_find[0])


def _count_pvs_with_parts(
    pvs: set[str], named_parts: set[str]
) -> list[tuple[str, int]]:
    return [(part, sum(1 for pv in pvs if part in pv)) for part in named_parts]


def _map_pv_name_parts_to_pvs(pvs: set[str]) -> dict[str, set[str]]:
    all_parts: dict[str, set[str]] = {name: set() for name in PV_NAME_PARTS}
    for pv in pvs:
        for part_index, pv_part in enumerate(_get_pv_parts(pv)):
            all_parts[PV_NAME_PARTS[part_index]].add(pv_part)
    return all_parts


def _get_pv_parts_stats(pvs: set[str]) -> dict[str, list[tuple[str, int]]]:
    """Generate count of pvs with statistics per pv name part.

    Args:
        pvs (set[str]): Set of pvs

    Returns:
        count of each pv with specific part
    """
    all_parts = _map_pv_name_parts_to_pvs(pvs)

    out = {
        named_part_key: _count_pvs_with_parts(pvs, named_part_value)
        for named_part_key, named_part_value in all_parts.items()
    }
    # Sort the counts
    for named_part, named_part_value in out.items():
        out[named_part] = sorted(named_part_value, key=operator.itemgetter(1))
    return out


def log_pv_parts_stats(pvs: set[str]) -> None:
    """Log the number of pvs affected by statistics per part of the pv name.

    Args:
        pvs (set[str]): List of PVs with found statistics
    """
    pv_parts_stats = _get_pv_parts_stats(pvs)
    for pv_parts_stats_key, pv_parts_stats_value in pv_parts_stats.items():
        LOG.info(
            "PV Stats %s - %s", pv_parts_stats_key, json.dumps(pv_parts_stats_value)
        )


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
