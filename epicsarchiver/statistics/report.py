"""Generate a report detailing a list of statistics of Archiver pvs.

Examples:
    .. highlight:: python
    .. code-block:: python

        ReportConfig(
            query_limit=1000,
            time_minimum=timedelta(days=100),
            connection_drops_minimum=30,
            config_files="/config_files_dir",
            other_archiver=ArchiverAppliance("other_archiver.example.org"),
            mb_per_day_minimum=1000,
        )
        report = generate_all_stats(ArchiverAppliance("archiver.example.org"), config)


"""

import asyncio
import datetime
import enum
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import pytz
from rich.console import Console

from epicsarchiver import ArchiverAppliance
from epicsarchiver.channelfinder import ChannelFinder
from epicsarchiver.statistics._external_stats import (
    get_double_archived,
    get_iocs,
    get_not_configured,
)
from epicsarchiver.statistics.stat_responses import (
    UNKNOWN_IOC,
    BaseStatResponse,
    DroppedReason,
    Ioc,
)

LOG: logging.Logger = logging.getLogger(__name__)


@dataclass
class ReportConfig:
    """Configurration for generating the report."""

    query_limit: int | None
    time_minimum: timedelta
    connection_drops_minimum: int
    config_files: Path | None
    other_archiver: ArchiverAppliance | None
    mb_per_day_minimum: float
    events_dropped_minimum: int
    channelfinder: ChannelFinder | None


class Stat(str, enum.Enum):
    """List of statistics from the archiver.

    Args:
        enum (Stat): A statistic on pvs in archiver
    """

    BufferOverflow = "PV updating faster than the sampling period."
    TypeChange = "PV changed type, which archiver hasn't been updated for."
    IncorrectTimestamp = "PV loses events due to incorrect timestamps."
    SlowChanging = "More events lost than stored."
    DisconnectedPVs = "PV disconnected for a long time."
    SilentPVs = "Never received a valid event."
    DoubleArchived = "Archived in both clusters."
    StorageRates = "In the top storage rates."
    LostConnection = "In the top dropped connections."
    NotConfigured = "PV archived, but not in config."

    @classmethod
    def _is_greater_than_time_minimum(
        cls, in_time: datetime.datetime | None, time_minimum: timedelta
    ) -> bool:
        now = datetime.datetime.now(tz=pytz.utc)
        diff = now - (
            in_time
            if in_time is not None
            else datetime.datetime.fromtimestamp(0, tz=pytz.utc)
        )
        return diff > time_minimum

    async def _response_report_dict(
        self, responses: Sequence[BaseStatResponse]
    ) -> dict[str, BaseStatResponse]:
        LOG.info("Found %s satisfying stat %s", len(responses), self)
        return {r.pv_name: r for r in responses}

    async def _get_responses(
        self,
        archiver: ArchiverAppliance,
        config: ReportConfig,
    ) -> Sequence[BaseStatResponse]:
        """Produce a list of PVs and stats."""
        match self:
            case Stat.BufferOverflow:
                return [
                    f
                    for f in archiver.get_pvs_dropped(
                        DroppedReason.BufferOverflow, limit=config.query_limit
                    )
                    if f.events_dropped > config.events_dropped_minimum
                ]

            case Stat.TypeChange:
                return archiver.get_pvs_dropped(
                    DroppedReason.TypeChange, limit=config.query_limit
                )

            case Stat.IncorrectTimestamp:
                return [
                    f
                    for f in archiver.get_pvs_dropped(
                        DroppedReason.IncorrectTimestamp, limit=config.query_limit
                    )
                    if f.events_dropped > config.events_dropped_minimum
                ]

            case Stat.SlowChanging:
                return [
                    f
                    for f in archiver.get_pvs_dropped(
                        DroppedReason.SlowChanging, limit=None
                    )
                    if f.events_dropped > config.events_dropped_minimum
                ]

            case Stat.DisconnectedPVs:
                return [
                    ev
                    for ev in archiver.get_disconnected_pvs()
                    if Stat._is_greater_than_time_minimum(
                        ev.connection_lost_at, config.time_minimum
                    )
                ]

            case Stat.SilentPVs:
                return [
                    ev
                    for ev in archiver.get_silent_pvs(limit=config.query_limit)
                    if Stat._is_greater_than_time_minimum(
                        ev.last_known_event, config.time_minimum
                    )
                ]

            case Stat.LostConnection:
                return [
                    el
                    for el in archiver.get_lost_connections_pvs(
                        limit=config.query_limit
                    )
                    if el.lost_connections > config.connection_drops_minimum
                ]

            case Stat.StorageRates:
                return [
                    r
                    for r in archiver.get_storage_rates(limit=config.query_limit)
                    if r.mb_per_day > config.mb_per_day_minimum
                ]

            case Stat.DoubleArchived:
                if config.other_archiver:
                    return await get_double_archived(archiver, config.other_archiver)
                return []

            case Stat.NotConfigured:
                if config.config_files:
                    return await get_not_configured(
                        archiver, config.channelfinder, config.config_files
                    )
                return []

    async def generate_stats(
        self,
        archiver: ArchiverAppliance,
        config: ReportConfig,
    ) -> dict[str, BaseStatResponse]:
        """Produce a list of PVs and stats."""
        return await self._response_report_dict(
            await self._get_responses(archiver, config)
        )


def print_report(
    archiver: ArchiverAppliance,
    config: ReportConfig,
    console: Console,
    *,
    verbose: bool = False,
) -> None:
    """Prints a report about the statitics of PVs in the archiver.

    Args:
        archiver (ArchiverAppliance): Archiver to get statistics
        config (ReportConfig): Configuration of the report
        console (Console): console where to print the report
        verbose (bool, optional): Verbose output or not. Defaults to False.
    """
    report = asyncio.run(generate_all_stats(archiver, config))
    if verbose:
        console.print(report)
        return
    sum_report = _summary_report(report)
    console.print_json(data=sum_report)


@dataclass
class _PVStats:
    name: str
    stats: dict[Stat, BaseStatResponse]

    def json_str(self) -> dict[str, str]:
        return {s.name: str(self.stats[s]) for s in self.stats}


async def generate_all_stats(
    archiver: ArchiverAppliance,
    config: ReportConfig,
) -> dict[Ioc, dict[str, _PVStats]]:
    """Generate all the statistics available from the Stat list and collate into a dict.

    Args:
        archiver (ArchiverAppliance): Archiver to get statistics from
        config (ReportConfig): Configuration of the report

    Returns:
        dict[Ioc, dict[str, _PVStats]]: Return a dictionary with pv names as keys,
          and detailed statistics after.
    """
    gather_all_stats = await asyncio.gather(*[
        stat.generate_stats(archiver, config) for stat in Stat
    ])
    inverted_data = _invert_data(dict(zip(list(Stat), gather_all_stats, strict=True)))
    if config.channelfinder:
        return await _organise_by_ioc(
            inverted_data,
            config.channelfinder,
        )
    return {UNKNOWN_IOC: inverted_data}


async def _organise_by_ioc(
    inverted_report: dict[str, _PVStats],
    channelfinder: ChannelFinder,
) -> dict[Ioc, dict[str, _PVStats]]:
    iocs = await get_iocs(channelfinder, list(inverted_report.keys()))
    LOG.info("IOCS: %s", str(await _iocs_summary(iocs)))
    return {ioc: {pv: inverted_report[pv] for pv in iocs[ioc]} for ioc in iocs}


async def _iocs_summary(iocs: dict[Ioc, list[str]]) -> list[str]:
    sorted_iocs = [(ioc, len(pvs)) for ioc, pvs in iocs.items()]
    sorted_iocs = sorted(sorted_iocs, key=lambda pair: pair[1])
    return [f"{ioc_pair[0]}:{ioc_pair[1]} PVs" for ioc_pair in sorted_iocs]


def _summary_report(
    report: dict[Ioc, dict[str, _PVStats]],
) -> dict[str, dict[str, dict[str, str]]]:
    """Creates a pure string and dictionary data output summary of the generated data.

      Easily converted to json and creates a sample output of

     .. code-block:: json

        "IOCName iocHostName": {
            "PV:1": {
                "TypeChange": "Dropped 31 events by TypeChange"
            },
            "PV:2": {
                "NotConfigured": "Archived but not in config."
            },
            "PV:3": {
                "DisconnectedPVs": "Disconnected 136 days ago, last event at None",
                "SilentPVs": "No events stored, last invalid event recieved at None"
            },
        }

    Args:
          report (dict[str, _PVStats]): Base input data in form of
            pv mapped to Stat and responses from the archiver.

    Returns:
          dict[str, dict[str, str]]: pv to dictionary of Stat name and problem summary
    """
    summary_report: dict[str, dict[str, dict[str, str]]] = {}

    for ioc, pvs in report.items():
        pv_summary_report: dict[str, dict[str, str]] = {}

        for pv, issue in pvs.items():
            pv_summary_report[pv] = issue.json_str()
        summary_report[f"IOC:{ioc.name}, host:{ioc.hostname}"] = pv_summary_report
    return dict(sorted(summary_report.items()))


def _invert_data(data: dict[Stat, dict[str, BaseStatResponse]]) -> dict[str, _PVStats]:
    """Inverts data from being by statistic, to be by PV.

    Args:
        data (dict[Stat, dict[str, BaseStatResponse]]): Input data with Stats to
            dictionary with pv name keys

    Returns:
        dict[str, _PVStats]: Output with Pv name keys.
    """
    dict_data: dict[str, dict[Stat, BaseStatResponse]] = {}
    for stat in data:
        for pv in data[stat]:
            if pv not in dict_data:
                dict_data[pv] = {}
            dict_data[pv][stat] = data[stat][pv]
    output = {pv: _PVStats(pv, dict_data[pv]) for pv in dict_data}
    return dict(sorted(output.items()))
