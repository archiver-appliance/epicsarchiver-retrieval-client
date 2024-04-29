"""Command module."""

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import click
from pytz import UTC
from rich.console import Console
from rich.table import Table

from epicsarchiver.common.command import handle_debug

if TYPE_CHECKING:
    from epicsarchiver.epicsarchiver import ArchiverAppliance

LOG: logging.Logger = logging.getLogger(__name__)


DATE_FORMATS = ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]


@click.command()
@click.option(
    "--debug",
    is_flag=True,
    callback=handle_debug,
    show_default=True,
    help="Turn on debug logging",
)
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
