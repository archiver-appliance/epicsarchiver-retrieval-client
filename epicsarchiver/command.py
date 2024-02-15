"""Command module."""

import logging
from datetime import datetime, timedelta
from pathlib import Path

import click
from pytz import UTC
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from epicsarchiver.channelfinder import ChannelFinder
from epicsarchiver.epicsarchiver import ArchiverAppliance
from epicsarchiver.statistics.report import ReportConfig, print_report

LOG: logging.Logger = logging.getLogger(__name__)


def _handle_debug(
    _ctx: click.core.Context | None,
    _param: click.core.Option | click.core.Parameter | None,
    debug: bool | int | str,  # noqa: FBT001
) -> bool | int | str:
    """Turn on DEBUG logs, if asked otherwise INFO default."""
    format_msg = "%(message)s"

    if debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format=format_msg,
            datefmt="[%X]",
            handlers=[RichHandler(rich_tracebacks=True)],
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format=format_msg,
            datefmt="[%X]",
            handlers=[RichHandler()],
        )
    return debug


@click.group()
@click.version_option()
@click.option(
    "--hostname",
    "-h",
    default="localhost",
    type=str,
    help="Achiver Appliance hostname or IP [default: localhost]",
)
@click.pass_context
def cli(ctx: click.core.Context, hostname: str) -> None:
    """Command line tool for interacting with the archiver."""
    ctx.obj = {"archiver": ArchiverAppliance(hostname)}


@click.option(
    "--debug",
    is_flag=True,
    callback=_handle_debug,
    show_default=True,
    help="Turn on debug logging",
)
@cli.command()
@click.option(
    "--appliance",
    default=None,
    type=str,
    help="Force PVs to be archived on the specified appliance (in a cluster)",
)
@click.argument("files", nargs=-1, type=click.Path(exists=True))
@click.pass_context
def archive(
    ctx: click.core.Context,
    appliance: str,
    files: list[str],
    debug: bool,  # noqa: FBT001, ARG001
) -> None:
    """Archive all PVs included in the files passed as parameters.

    The files shall be in CSV format (space separated) and include one PV name per line.
    A file can also include the name of the policy to force (optional).
    Empty lines and lines starting with "#" (comments) are allowed.

    Here is an example::

        # PV name    Policy
        ISrc-010:PwrC-CoilPS-01:CurS
        ISrc-010:PwrC-CoilPS-01:CurR slow
        # Comments are allowed
        LEBT-010:Vac-VCG-30000:PrsStatR

    The "slow" policy will be forced for the second PV.
    Check the help for more information.
    """
    archiver: ArchiverAppliance = ctx.obj["archiver"]
    res = archiver.archive_pvs_from_files(files, appliance)
    LOG.debug(res)
    ctx.exit(0)


@click.option(
    "--debug",
    is_flag=True,
    callback=_handle_debug,
    show_default=True,
    help="Turn on debug logging",
)
@cli.command()
@click.argument(
    "files",
    nargs=-1,
    type=click.Path(exists=True),
)
@click.pass_context
def rename(
    ctx: click.core.Context,
    files: list[str],
    debug: bool,  # noqa: FBT001, ARG001
) -> None:
    """Rename all PVs included in the files passed as parameters.

    Each PV will be paused, renamed and resumed. The old name remains paused.

    .. code-block:: console

        epicsarchiver --hostname archiver-01.example.com rename file1 file2

    The files shall be in CSV format (space separated) and include the current PV name
    and the new one.
    Empty lines and lines starting with "#" (comments) are allowed.

    Here is an example::

        # PV current name                 new name
        ISrc-010:PwrC-CoilPS-01:CurS ISrc-010:PwrC-CoilPS-02:CurS
        ISrc-010:PwrC-CoilPS-01:CurR ISrc-010:PwrC-CoilPS-02:CurR
        # Comments are allowed
        LEBT-010:Vac-VCG-30000:PrsStatR LEBT-010:Vac-VCG-30001
    """
    archiver: ArchiverAppliance = ctx.obj["archiver"]
    archiver.rename_pvs_from_files(files)
    ctx.exit(0)


@click.option(
    "--debug",
    is_flag=True,
    callback=_handle_debug,
    show_default=True,
    help="Turn on debug logging",
)
@cli.command()
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
    "--config_files",
    "-d",
    type=click.Path(exists=True, dir_okay=True, path_type=Path, resolve_path=True),
    help="Files with lists of PVs",
)
@click.argument(
    "output",
    type=click.Path(exists=False, path_type=Path, resolve_path=True),
)
@click.pass_context
def stats(
    ctx: click.core.Context,
    limit: int,
    other_hostname: str | None,
    time_minimum: int,
    connection_drops_minimum: int,
    config_files: Path | None,
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

    with open(output, "w", encoding="locale") as out_file:
        config = ReportConfig(
            query_limit=limit,
            time_minimum=timedelta(days=time_minimum),
            connection_drops_minimum=connection_drops_minimum,
            config_files=config_files,
            other_archiver=other_archiver,
            mb_per_day_minimum=mb_per_day_minimum,
            events_dropped_minimum=events_dropped_minimum,
            channelfinder=channelfinder,
            ioc_name=ioc,
        )
        LOG.info("Collecting statistics with configuration %s", config)

        print_report(archiver, config, out_file, verbose=verbose)
    ctx.exit(0)


DATE_FORMATS = ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]


@click.option(
    "--debug",
    is_flag=True,
    callback=_handle_debug,
    show_default=True,
    help="Turn on debug logging",
)
@cli.command()
@click.option(
    "--start",
    "-s",
    default=(datetime.now(tz=UTC) - timedelta(seconds=30)).strftime(DATE_FORMATS[2]),
    type=click.DateTime(formats=DATE_FORMATS),
    help="Start time of query",
)
@click.option(
    "--end",
    "-e",
    default=str(datetime.now(tz=UTC).strftime(DATE_FORMATS[2])),
    type=click.DateTime(formats=DATE_FORMATS),
    help="End time of query",
)
@click.argument(
    "pv",
    type=str,
)
@click.pass_context
def get(
    ctx: click.core.Context,
    pv: str,
    start: datetime,
    end: datetime,
    debug: bool,  # noqa: FBT001, ARG001
) -> None:
    """Print out data from an archiver cluster.

    ARGUEMENT pv What pv to get data of.

    Example usage:

    .. code-block:: console

        epicsarchiver --hostname archiver-01.example.com get PV_NAME

    """
    archiver: ArchiverAppliance = ctx.obj["archiver"]
    console = Console()
    events = archiver.get_events(pv, start, end)
    table = Table(title=f"PV {pv} Events from: {start} to: {end}")
    table.add_column("Time", justify="left")
    table.add_column("Value", justify="right")
    table.add_column("Status", justify="right")
    table.add_column("Severity", justify="right")
    for e in events:
        table.add_row(str(e.pd_timestamp), str(e.val), str(e.status), str(e.severity))
    console.print(table)
    ctx.exit(0)
