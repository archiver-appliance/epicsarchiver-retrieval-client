"""Generate a report detailing a list of statistics of Archiver pvs.

Examples:
    .. highlight:: python
    .. code-block:: python

        ReportConfig(
            query_limit=1000,
            time_minimum=timedelta(days=100),
            connection_drops_minimum=30,
            config_options=configuration.ConfigOptions("/config_repo", "tn"),
            other_archiver=ArchiverAppliance("other_archiver.example.org"),
            mb_per_day_minimum=1000,
        )
        report = generate_all_stats(ArchiverAppliance("archiver.example.org"), config)


"""

from __future__ import annotations

import asyncio
import csv
import dataclasses
import datetime
import enum
import json
import logging
import operator
import re
import sys
from dataclasses import dataclass
from datetime import timedelta
from typing import IO, TYPE_CHECKING, Any

import pytz
from rich.console import Console

from epicsarchiver.statistics import configuration
from epicsarchiver.statistics._external_stats import (
    filter_by_ioc,
    get_double_archived,
    get_invalid_names,
    get_iocs,
)
from epicsarchiver.statistics.stat_responses import (
    UNKNOWN_IOC,
    BaseStatResponse,
    DroppedReason,
    Ioc,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from epicsarchiver.statistics.archiver_statistics import ArchiverWrapper
    from epicsarchiver.statistics.channelfinder import ChannelFinder

LOG: logging.Logger = logging.getLogger(__name__)


def _is_greater_than_time_minimum(
    in_time: datetime.datetime | None,
    time_minimum: timedelta,
) -> bool:
    now = datetime.datetime.now(tz=pytz.utc)
    diff = now - (in_time or datetime.datetime.fromtimestamp(0, tz=pytz.utc))
    return diff > time_minimum


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
    InvalidName = "PV has name that should not be archived"


CSV_HEADINGS = [
    "IOC Name",
    "IOC hostname",
    "PV name",
    "Statistic",
    "Statistic Note",
]

PV_NAME_REGEX = r"(?P<system>[a-zA-Z0-9\-]+):(?P<device>[a-zA-Z\-]+)\-[0-9a-zA-Z]+:*"
PV_NAME_PARTS = ["system", "device"]


def _get_pv_parts(pv: str) -> list[str]:
    regex_find = re.findall(PV_NAME_REGEX, pv)
    if len(regex_find) != 1:
        LOG.debug("pv %s does not match regex", pv)
        return []
    return list(regex_find[0])


def _get_pv_parts_stats(pvs: set[str]) -> dict[str, list[tuple[str, int]]]:
    """Generate json summary of input based on system.

    Args:
        pvs (set[str]): Set of pvs

    Returns:
        count of each pv with specific part
    """
    all_parts: dict[str, set[str]] = {name: set() for name in PV_NAME_PARTS}
    for pv in pvs:
        for part_index, pv_part in enumerate(_get_pv_parts(pv)):
            all_parts[PV_NAME_PARTS[part_index]].add(pv_part)

    out = {
        named_part_key: [
            (part, sum(1 for pv in pvs if part in pv)) for part in named_part_value
        ]
        for named_part_key, named_part_value in all_parts.items()
    }
    for named_part, named_part_value in out.items():
        out[named_part] = sorted(named_part_value, key=operator.itemgetter(1))
    return out


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
    config_options: configuration.ConfigOptions | None
    other_archiver: ArchiverWrapper | None
    mb_per_day_minimum: float
    events_dropped_minimum: int
    channelfinder: ChannelFinder
    ioc_name: str | None

    async def _get_responses(  # noqa: PLR0911, C901, PLR0912
        self,
        statistic: Stat,
        archiver: ArchiverWrapper,
    ) -> Sequence[BaseStatResponse]:
        """Produce a list of PVs and stats.

        Args:
            statistic (Stat): Statistic to fetch
            archiver (ArchiverWrapper): Archiver to request against

        Returns:
            Sequence[BaseStatResponse]: Sequence of statistic responses
        """
        if statistic == Stat.BufferOverflow:
            return [
                f
                for f in await archiver.stats.get_pvs_dropped(
                    DroppedReason.BufferOverflow,
                    limit=self.query_limit,
                )
                if f.events_dropped > self.events_dropped_minimum
            ]

        if statistic == Stat.TypeChange:
            return await archiver.stats.get_pvs_dropped(
                DroppedReason.TypeChange,
                limit=self.query_limit,
            )

        if statistic == Stat.IncorrectTimestamp:
            return [
                f
                for f in await archiver.stats.get_pvs_dropped(
                    DroppedReason.IncorrectTimestamp,
                    limit=self.query_limit,
                )
                if f.events_dropped > self.events_dropped_minimum
            ]

        if statistic == Stat.SlowChanging:
            return [
                f
                for f in await archiver.stats.get_pvs_dropped(
                    DroppedReason.SlowChanging,
                    limit=None,
                )
                if f.events_dropped > self.events_dropped_minimum
            ]

        if statistic == Stat.DisconnectedPVs:
            return [
                ev
                for ev in await archiver.stats.get_disconnected_pvs()
                if _is_greater_than_time_minimum(
                    ev.connection_lost_at,
                    self.time_minimum,
                )
            ]

        if statistic == Stat.SilentPVs:
            silent_pvs = await archiver.stats.get_silent_pvs(limit=self.query_limit)
            return [
                ev
                for ev in silent_pvs
                if _is_greater_than_time_minimum(
                    ev.last_known_event,
                    self.time_minimum,
                )
            ]

        if statistic == Stat.LostConnection:
            return [
                el
                for el in await archiver.stats.get_lost_connections_pvs(
                    limit=self.query_limit,
                )
                if el.lost_connections > self.connection_drops_minimum
            ]

        if statistic == Stat.StorageRates:
            storage_rates = await archiver.stats.get_storage_rates(
                limit=self.query_limit
            )
            return [r for r in storage_rates if r.mb_per_day > self.mb_per_day_minimum]

        if statistic == Stat.DoubleArchived:
            if self.other_archiver:
                return await get_double_archived(archiver, self.other_archiver)
            return []

        if statistic == Stat.NotConfigured:
            if self.config_options:
                return await configuration.get_not_configured(
                    archiver,
                    self.channelfinder,
                    self.config_options,
                    self.ioc_name,
                )
            return []
        if statistic == Stat.InvalidName:
            return await get_invalid_names(archiver)
        return []

    async def generate_stats(
        self,
        statistic: Stat,
        archiver: ArchiverWrapper,
    ) -> dict[str, BaseStatResponse]:
        """Produce a list of PVs and stats.

        Args:
            statistic (Stat): Statistic to generate data from
            archiver (ArchiverWrapper): Archiver to check against

        Returns:
            dict[str, BaseStatResponse]: dictionary of pvs to statistics
        """
        responses = await self._get_responses(statistic, archiver)
        LOG.info("Found %s responses for %s", len(responses), statistic)
        return {r.pv_name: r for r in responses}

    async def generate(
        self,
        archiver: ArchiverWrapper,
    ) -> dict[Ioc, dict[str, PVStats]]:
        """Generate all the statistics available from the Stat list.

        Args:
            archiver (ArchiverWrapper): Archiver to get statistics from

        Returns:
            dict[Ioc, dict[str, PVStats]]: Return a dictionary with pv names as keys,
            and detailed statistics after.
        """
        gather_all_stats = await asyncio.gather(*[
            self.generate_stats(stat, archiver) for stat in Stat
        ])
        inverted_data = _invert_data(dict(zip(list(Stat), gather_all_stats)))
        pvs = set(inverted_data.keys())
        pv_parts_stats = _get_pv_parts_stats(pvs)
        for pv_parts_stats_key, pv_parts_stats_value in pv_parts_stats.items():
            LOG.info(
                "PV Stats %s - %s", pv_parts_stats_key, json.dumps(pv_parts_stats_value)
            )
        if self.channelfinder:
            return await _organise_by_ioc(
                inverted_data,
                self.channelfinder,
                ioc_name=self.ioc_name,
            )
        return {UNKNOWN_IOC: inverted_data}

    def print_report(
        self,
        archiver: ArchiverWrapper,
        file: IO[str],
        *,
        verbose: bool = False,
    ) -> None:
        """Prints a report about the statistics of PVs in the archiver.

        Args:
            archiver (ArchiverWrapper): Archiver to get statistics
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
        csvwriter.writerow(CSV_HEADINGS)
        for row in sum_report:
            csvwriter.writerow(row)


@dataclass
class IocReport:
    """Data for generating a report about an ioc connection to archiver.

    Args:
        ioc (str): Name of ioc
        channelfinder (ChannelFinder): Channelfinder to get pv info of ioc
        archiver (ArchiverWrapper): Archiver to check
        config_gitlab_repo: Path | None
    """

    ioc_name: str
    channelfinder: ChannelFinder
    archiver: ArchiverWrapper
    mb_per_day_minimum: float
    config_options: configuration.ConfigOptions | None

    def print_report(self) -> None:
        """Print report about the statistics of connections from IOC to archiver."""
        report = asyncio.run(self.generate())
        csv_sum_report = csv_output(report)
        csvwriter = csv.writer(sys.stdout)
        csvwriter.writerow(CSV_HEADINGS)
        for row in csv_sum_report:
            csvwriter.writerow(row)

    async def generate(self) -> dict[Ioc, dict[str, PVStats]]:
        """Generate all the statistics data for an ioc.

        Returns:
            dict[Ioc, dict[str, _PVStats]]: statistics list
        """
        # Get all pvs on IOC
        channels = await self.channelfinder.get_ioc_channels(self.ioc_name)
        LOG.info("Found %s PVs in ChannelFinder", len(channels))
        if len(channels) < 0:
            return {}

        pv_names = {pv.name for pv in channels}
        pv_details = await self._get_archived_pvs_details(pv_names)
        if self.config_options:
            await self._check_not_configured(pv_names, pv_details, self.config_options)

        return {Ioc.from_channel(channels[0]): pv_details}

    async def _check_not_configured(
        self,
        pv_names: set[str],
        pv_details: dict[str, PVStats],
        config_options: configuration.ConfigOptions,
    ) -> None:
        not_configured = await configuration.get_not_configured(
            self.archiver,
            self.channelfinder,
            config_options,
            self.ioc_name,
            pv_names,
        )
        for pv_not in not_configured:
            if pv_not.pv_name not in pv_details:
                pv_details[pv_not.pv_name] = PVStats(pv_not.pv_name, {})
            pv_details[pv_not.pv_name].stats[Stat.NotConfigured] = pv_not

    async def _get_archived_pvs_details(self, pv_names: set[str]) -> dict[str, PVStats]:
        all_archived = self.archiver.mgmt.get_archived_pvs(list(pv_names))
        archived_pvs = set(all_archived).intersection(pv_names)
        return await self.archiver.stats.get_pv_details(
            list(archived_pvs), self.mb_per_day_minimum
        )


class _EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)  # type: ignore[arg-type]
        return super().default(o)


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
    LOG.info("IOCS: %s", json.dumps(_iocs_summary(iocs), cls=_EnhancedJSONEncoder))
    return {ioc: {pv: inverted_report[pv] for pv in iocs[ioc]} for ioc in iocs}


def _iocs_summary(iocs: dict[Ioc, list[str]]) -> list[tuple[Ioc, int]]:
    sorted_iocs = [(ioc, len(pvs)) for ioc, pvs in iocs.items()]
    return sorted(sorted_iocs, key=operator.itemgetter(1))


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
    for stat, stat_item in data.items():
        for pv in stat_item:
            if pv not in dict_data:
                dict_data[pv] = {}
            dict_data[pv][stat] = stat_item[pv]
    output = {pv: PVStats(pv, dict_data[pv]) for pv in dict_data}
    return dict(sorted(output.items()))
