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

from __future__ import annotations

import asyncio
import csv
import datetime
import enum
import logging
import operator
from dataclasses import dataclass
from datetime import timedelta
from typing import IO, TYPE_CHECKING

import pytz
from rich.console import Console

from epicsarchiver.statistics._external_stats import (
    filter_by_ioc,
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

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from epicsarchiver.epicsarchiver import ArchiverAppliance
    from epicsarchiver.statistics.channelfinder import ChannelFinder

LOG: logging.Logger = logging.getLogger(__name__)


def _is_greater_than_time_minimum(
    in_time: datetime.datetime | None,
    time_minimum: timedelta,
) -> bool:
    now = datetime.datetime.now(tz=pytz.utc)
    diff = now - (in_time or datetime.datetime.fromtimestamp(0, tz=pytz.utc))
    return diff > time_minimum


def _response_report_dict(
    responses: Sequence[BaseStatResponse],
) -> dict[str, BaseStatResponse]:
    LOG.info("Found %s responses", len(responses))
    return {r.pv_name: r for r in responses}


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


@dataclass
class PVStats:
    """Statistics of a PV.

    name: PV Name
    stats: Dictionary of Statistic type to BaseStatResponse with more details.
    """

    name: str
    stats: dict[Stat, BaseStatResponse]


@dataclass
class ArchiverReport:
    """Configuration for generating the report."""

    query_limit: int | None
    time_minimum: timedelta
    connection_drops_minimum: int
    config_gitlab_repo: Path | None
    other_archiver: ArchiverAppliance | None
    mb_per_day_minimum: float
    events_dropped_minimum: int
    channelfinder: ChannelFinder | None
    ioc_name: str | None

    async def _get_responses(  # noqa: PLR0911, C901
        self,
        statistic: Stat,
        archiver: ArchiverAppliance,
    ) -> Sequence[BaseStatResponse]:
        """Produce a list of PVs and stats."""
        if statistic == Stat.BufferOverflow:
            return [
                f
                for f in archiver.get_pvs_dropped(
                    DroppedReason.BufferOverflow,
                    limit=self.query_limit,
                )
                if f.events_dropped > self.events_dropped_minimum
            ]

        if statistic == Stat.TypeChange:
            return archiver.get_pvs_dropped(
                DroppedReason.TypeChange,
                limit=self.query_limit,
            )

        if statistic == Stat.IncorrectTimestamp:
            return [
                f
                for f in archiver.get_pvs_dropped(
                    DroppedReason.IncorrectTimestamp,
                    limit=self.query_limit,
                )
                if f.events_dropped > self.events_dropped_minimum
            ]

        if statistic == Stat.SlowChanging:
            return [
                f
                for f in archiver.get_pvs_dropped(
                    DroppedReason.SlowChanging,
                    limit=None,
                )
                if f.events_dropped > self.events_dropped_minimum
            ]

        if statistic == Stat.DisconnectedPVs:
            return [
                ev
                for ev in archiver.get_disconnected_pvs()
                if _is_greater_than_time_minimum(
                    ev.connection_lost_at,
                    self.time_minimum,
                )
            ]

        if statistic == Stat.SilentPVs:
            return [
                ev
                for ev in archiver.get_silent_pvs(limit=self.query_limit)
                if _is_greater_than_time_minimum(
                    ev.last_known_event,
                    self.time_minimum,
                )
            ]

        if statistic == Stat.LostConnection:
            return [
                el
                for el in archiver.get_lost_connections_pvs(
                    limit=self.query_limit,
                )
                if el.lost_connections > self.connection_drops_minimum
            ]

        if statistic == Stat.StorageRates:
            return [
                r
                for r in archiver.get_storage_rates(limit=self.query_limit)
                if r.mb_per_day > self.mb_per_day_minimum
            ]

        if statistic == Stat.DoubleArchived:
            if self.other_archiver:
                return await get_double_archived(archiver, self.other_archiver)
            return []

        if statistic == Stat.NotConfigured:
            if self.config_gitlab_repo:
                return await get_not_configured(
                    archiver,
                    self.channelfinder,
                    self.config_gitlab_repo,
                    self.ioc_name,
                )
            return []
        return []

    async def generate_stats(
        self,
        statistic: Stat,
        archiver: ArchiverAppliance,
    ) -> dict[str, BaseStatResponse]:
        """Produce a list of PVs and stats."""
        return _response_report_dict(await self._get_responses(statistic, archiver))

    async def generate(
        self,
        archiver: ArchiverAppliance,
    ) -> dict[Ioc, dict[str, PVStats]]:
        """Generate all the statistics available from the Stat list.

        Args:
            archiver (ArchiverAppliance): Archiver to get statistics from

        Returns:
            dict[Ioc, dict[str, PVStats]]: Return a dictionary with pv names as keys,
            and detailed statistics after.
        """
        gather_all_stats = await asyncio.gather(*[
            self.generate_stats(stat, archiver) for stat in Stat
        ])
        inverted_data = _invert_data(dict(zip(list(Stat), gather_all_stats)))
        if self.channelfinder:
            return await _organise_by_ioc(
                inverted_data,
                self.channelfinder,
                ioc_name=self.ioc_name,
            )
        return {UNKNOWN_IOC: inverted_data}

    def print_report(
        self,
        archiver: ArchiverAppliance,
        file: IO[str],
        *,
        verbose: bool = False,
    ) -> None:
        """Prints a report about the statitics of PVs in the archiver.

        Args:
            archiver (ArchiverAppliance): Archiver to get statistics
            file (IO[str]): file to print the report to
            verbose (bool, optional): Verbose output or not. Defaults to False.
        """
        report = asyncio.run(self.generate(archiver))
        if verbose:
            console = Console(file=file)
            console.print(report)
            return
        sum_report = csv_output(report)
        csvwriter = csv.writer(file)
        csvwriter.writerow([
            "IOC Name",
            "IOC hostname",
            "PV name",
            "Statistic",
            "Statistic Note",
        ])
        for row in sum_report:
            csvwriter.writerow(row)


async def _organise_by_ioc(
    inverted_report: dict[str, PVStats],
    channelfinder: ChannelFinder,
    ioc_name: str | None = None,
) -> dict[Ioc, dict[str, PVStats]]:
    if ioc_name:
        iocs = await filter_by_ioc(
            channelfinder,
            ioc_name,
            list(inverted_report.keys()),
        )
    else:
        iocs = await get_iocs(channelfinder, list(inverted_report.keys()))
    LOG.info("IOCS: %s", str(_iocs_summary(iocs)))
    return {ioc: {pv: inverted_report[pv] for pv in iocs[ioc]} for ioc in iocs}


def _iocs_summary(iocs: dict[Ioc, list[str]]) -> list[str]:
    sorted_iocs = [(ioc, len(pvs)) for ioc, pvs in iocs.items()]
    sorted_iocs = sorted(sorted_iocs, key=operator.itemgetter(1))
    return [f"{ioc_pair[0]}:{ioc_pair[1]} PVs" for ioc_pair in sorted_iocs]


def csv_output(
    report: dict[Ioc, dict[str, PVStats]],
) -> list[list[str]]:
    """Creates a list[str] output of the generated data for printing as csv.

    Outs with headings: IOC Name, IOC hostname, PV name, Statistic, Statistic Note

    Args:
          report (dict[str, PVStats]): Base input data in form of
            pv mapped to Stat and responses from the archiver.

    Returns:
          list[list[str]]: List of list of strings
    """
    return [
        [ioc.name, ioc.hostname, pv, stat.name, str(stat_note)]
        for ioc, pvs in report.items()
        for pv, issue in pvs.items()
        for stat, stat_note in issue.stats.items()
    ]


def _invert_data(data: dict[Stat, dict[str, BaseStatResponse]]) -> dict[str, PVStats]:
    """Inverts data from being by statistic, to be by PV.

    Args:
        data (dict[Stat, dict[str, BaseStatResponse]]): Input data with Stats to
            dictionary with pv name keys

    Returns:
        dict[str, PVStats]: Output with Pv name keys.
    """
    dict_data: dict[str, dict[Stat, BaseStatResponse]] = {}
    for stat in data:
        for pv in data[stat]:
            if pv not in dict_data:
                dict_data[pv] = {}
            dict_data[pv][stat] = data[stat][pv]
    output = {pv: PVStats(pv, dict_data[pv]) for pv in dict_data}
    return dict(sorted(output.items()))
