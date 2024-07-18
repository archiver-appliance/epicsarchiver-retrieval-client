"""Command module."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from pathlib import Path

import click

from epicsarchiver.common.command import handle_debug
from epicsarchiver.statistics import configuration
from epicsarchiver.statistics.archiver_statistics import ArchiverWrapper
from epicsarchiver.statistics.channelfinder import ChannelFinder
from epicsarchiver.statistics.report import ArchiverReport, IocReport

LOG: logging.Logger = logging.getLogger(__name__)

ARCHIVER_ALIASES = ["tn", "nin", "lab"]


@click.command()
@click.option(
    "--debug",
    is_flag=True,
    callback=handle_debug,
    show_default=True,
    help="Turn on debug logging",
)
@click.option(
    "--limit",
    "-l",
    default=1000,
    type=int,
    help="Limit size of queries",
)
@click.option(
    "--other_hostname",
    "-o",
    type=str,
    help="Other Achiver Appliance hostname or IP [default: localhost]",
)
@click.option(
    "--channelfinder",
    "-cf",
    default="channelfinder.tn.esss.lu.se",
    type=str,
    help="Channel Finder hostname or IP [default: channelfinder.tn.esss.lu.se]",
)
@click.option(
    "--time-minimum",
    "-t",
    default=100,
    type=int,
    help="Minimum time since last disconnect in days.",
)
@click.option(
    "--mb-per-day-minimum",
    "-mb",
    default=100,
    type=float,
    help="Minimum storage rate in MB/day",
)
@click.option(
    "--connection-drops-minimum",
    "-c",
    default=30,
    type=int,
    help="Minimum connection drops to see.",
)
@click.option(
    "--events-dropped-minimum",
    "-edm",
    default=10,
    type=int,
    help="Minimum event drops to see.",
)
@click.option(
    "--ioc",
    "-i",
    type=str,
    help="IOC to filter by.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    show_default=False,
    default=False,
    help="Verbose output",
)
@click.option(
    "--config-gitlab-repo",
    "-d",
    type=click.Path(path_type=Path),
    default="archiver-appliance/archiver-appliance-config-aa-linac-prod",
    help="Gitlab repo for files with lists of PVs",
)
@click.option(
    "--config-archiver-alias",
    type=click.Choice(ARCHIVER_ALIASES, case_sensitive=False),
    default="tn",
    help="Alias of the Archiver cluster chosen via info tag in IOC Record",
)
@click.argument(
    "output",
    type=click.Path(exists=False, path_type=Path, resolve_path=True),
)
@click.pass_context
def stats(  # noqa: PLR0917, PLR0913
    ctx: click.core.Context,
    limit: int,
    other_hostname: str | None,
    time_minimum: int,
    connection_drops_minimum: int,
    config_gitlab_repo: Path | None,
    config_archiver_alias: str | None,
    mb_per_day_minimum: float,
    events_dropped_minimum: int,
    channelfinder: str,
    ioc: str | None,
    verbose: bool,  # noqa: FBT001
    output: Path,
    debug: bool,  # noqa: FBT001, ARG001
) -> None:
    """Print out statistics from an archiver cluster.

    ARGUEMENT output Where to print output detailed statistics.

    Includes PVs that are often dropping events, long disconnected, producing no events
    and not configured. Example usage:

    .. code-block:: console

        epicsarchiver --hostname archiver-01.example.com stats output.csv

    By default produces a csv output in the form

    IOC Name, IOC hostname, PV name, Statistic, Statistic Note
    IOC_NAME, PV:NAME, BufferOverflow, Dropped 33393 events by BufferOverflow

    """
    archiver: ArchiverWrapper = ArchiverWrapper(ctx.obj["archiver"].hostname)
    other_archiver = (
        ArchiverWrapper(hostname=other_hostname) if other_hostname else None
    )
    channelfinder_service = ChannelFinder(channelfinder)

    try:
        with output.open("w") as out_file:
            report = ArchiverReport(
                query_limit=limit,
                time_minimum=timedelta(days=time_minimum),
                connection_drops_minimum=connection_drops_minimum,
                config_options=configuration.ConfigOptions(
                    config_gitlab_repo, config_archiver_alias
                ),
                other_archiver=other_archiver,
                mb_per_day_minimum=mb_per_day_minimum,
                events_dropped_minimum=events_dropped_minimum,
                channelfinder=channelfinder_service,
                ioc_name=ioc,
            )
            LOG.info("Collecting statistics with configuration %s", report)

            report.print_report(archiver, out_file, verbose=verbose)
    finally:
        # Close all the service clients
        asyncio.run(channelfinder_service.close())
        asyncio.run(archiver.close())
        if other_archiver:
            asyncio.run(other_archiver.close())

    ctx.exit(0)


@click.command()
@click.option(
    "--debug",
    is_flag=True,
    callback=handle_debug,
    show_default=True,
    help="Turn on debug logging",
)
@click.option(
    "--channelfinder",
    "-cf",
    default="channelfinder.tn.esss.lu.se",
    type=str,
    help="Channel Finder hostname or IP [default: channelfinder.tn.esss.lu.se]",
)
@click.option(
    "--config-gitlab-repo",
    "-d",
    type=click.Path(path_type=Path),
    help="Gitlab repo for files with lists of PVs",
)
@click.option(
    "--config-archiver-alias",
    type=click.Choice(ARCHIVER_ALIASES, case_sensitive=False),
    default="tn",
    help="Alias of the Archiver cluster chosen via info tag in IOC Record",
)
@click.option(
    "--mb-per-day-minimum",
    "-mb",
    default=100,
    type=float,
    help="Minimum storage rate in MB/day",
)
@click.argument(
    "ioc",
    type=str,
)
@click.pass_context
def ioc_check(  # noqa: PLR0917, PLR0913
    ctx: click.core.Context,
    ioc: str,
    config_gitlab_repo: Path | None,
    config_archiver_alias: str | None,
    mb_per_day_minimum: float,
    channelfinder: str,
    debug: bool,  # noqa: FBT001, ARG001
) -> None:
    """Print out statistics of a single IOC from an archiver cluster.

    ARGUMENT IOC Name of IOC to check
    """
    archiver: ArchiverWrapper = ArchiverWrapper(ctx.obj["archiver"].hostname)
    channelfinder_service = ChannelFinder(channelfinder)
    try:
        ioc_report = IocReport(
            ioc,
            channelfinder_service,
            archiver,
            mb_per_day_minimum,
            configuration.ConfigOptions(config_gitlab_repo, config_archiver_alias),
        )
        ioc_report.print_report()
    finally:
        # Close all the service clients
        asyncio.run(channelfinder_service.close())
        asyncio.run(archiver.close())
    ctx.exit(0)
