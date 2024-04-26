"""Command module."""

from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path

import click

from epicsarchiver.common.command import handle_debug
from epicsarchiver.epicsarchiver import ArchiverAppliance
from epicsarchiver.statistics.channelfinder import ChannelFinder
from epicsarchiver.statistics.report import ReportConfig, print_report

LOG: logging.Logger = logging.getLogger(__name__)


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
    "--channelfinder_hostname",
    "-cf",
    default="channelfinder.tn.esss.lu.se",
    type=str,
    help="Channel Finder hostname or IP [default: localhost]",
)
@click.option(
    "--time_minimum",
    "-t",
    default=100,
    type=int,
    help="Minimum time since last disconnect in days.",
)
@click.option(
    "--mb_per_day_minimum",
    "-mb",
    default=100,
    type=float,
    help="Minimum storage rate in MB/day",
)
@click.option(
    "--connection_drops_minimum",
    "-c",
    default=30,
    type=int,
    help="Minimum connection drops to see.",
)
@click.option(
    "--events_dropped_minimum",
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
    "--config_gitlab_repo",
    "-d",
    type=click.Path(path_type=Path),
    default="archiver-appliance/archiver-appliance-config-aa-linac-prod",
    help="Gitlab repo for files with lists of PVs",
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
    mb_per_day_minimum: float,
    events_dropped_minimum: int,
    channelfinder_hostname: str | None,
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
    archiver: ArchiverAppliance = ctx.obj["archiver"]
    other_archiver = (
        ArchiverAppliance(hostname=other_hostname) if other_hostname else None
    )
    channelfinder = (
        ChannelFinder(channelfinder_hostname) if channelfinder_hostname else None
    )

    with output.open("w") as out_file:
        config = ReportConfig(
            query_limit=limit,
            time_minimum=timedelta(days=time_minimum),
            connection_drops_minimum=connection_drops_minimum,
            config_gitlab_repo=config_gitlab_repo,
            other_archiver=other_archiver,
            mb_per_day_minimum=mb_per_day_minimum,
            events_dropped_minimum=events_dropped_minimum,
            channelfinder=channelfinder,
            ioc_name=ioc,
        )
        LOG.info("Collecting statistics with configuration %s", config)

        print_report(archiver, config, out_file, verbose=verbose)
    ctx.exit(0)
