"""Generate a report detailing a list of statistics of Archiver pvs from an IOC.

Examples:

    .. code-block:: python

        ioc_report = IocReport(
            "IOC_NAME",
            ChannelFinder("channelfinder.example.org"),
            ArchiverWrapper("archiver.example.org"),
            100,  # mb_per_day_minimum
            configuration.ConfigOptions("/config_repo", "tn"),
        )
        ioc_report.print_report()

"""

from __future__ import annotations

import asyncio
import csv
import logging
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from epicsarchiver.statistics import configuration
from epicsarchiver.statistics.models.stat_responses import Ioc
from epicsarchiver.statistics.models.stats import PVStats, Stat
from epicsarchiver.statistics.reports import REPORT_CSV_HEADINGS
from epicsarchiver.statistics.reports.archiver_report import csv_output

if TYPE_CHECKING:
    from epicsarchiver.statistics.services.archiver_statistics import ArchiverWrapper
    from epicsarchiver.statistics.services.channelfinder import ChannelFinder

LOG: logging.Logger = logging.getLogger(__name__)


@dataclass
class IocReport:
    """Data for generating a report about an ioc connection to archiver.

    Args:
        ioc_name (str): Name of ioc
        channelfinder (ChannelFinder): Channelfinder to get pv info of ioc
        archiver (ArchiverWrapper): Archiver to check
        mb_per_day_minimum (float): Minimum mb per day to filter on storage statistics
        config_options (configuration.ConfigOptions | None): configuration options
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
        csvwriter.writerow(REPORT_CSV_HEADINGS)
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
