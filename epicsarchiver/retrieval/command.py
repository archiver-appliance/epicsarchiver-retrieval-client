"""Command module."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import click
from pytz import UTC
from rich.console import Console
from rich.table import Table

from epicsarchiver.common.command import handle_debug
from epicsarchiver.retrieval.archiver_retrieval import Processor, ProcessorName

if TYPE_CHECKING:
    from epicsarchiver.epicsarchiver import ArchiverAppliance

LOG: logging.Logger = logging.getLogger(__name__)


DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S.%f",
]


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
@click.option(
    "--processor-name",
    "-p",
    type=click.Choice(
        [processor.name for processor in ProcessorName], case_sensitive=False
    ),
    help="PreProcessor to use",
)
@click.option(
    "--bin_size",
    "-b",
    type=int,
    help="Bin size (mostly in seconds) for preprocessor.",
)
@click.argument(
    "pv",
    type=str,
)
@click.pass_context
def get(  # noqa: PLR0917, PLR0913
    ctx: click.core.Context,
    pv: str,
    start: datetime,
    end: datetime,
    processor_name: str | None,
    bin_size: int | None,
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
    processor = (
        Processor(ProcessorName[processor_name.upper()], bin_size)
        if processor_name
        else None
    )
    events = archiver.get_events(pv, start, end, processor=processor)
    table_title = f"PV {pv}, Period {start} - {end}"
    if processor:
        table_title += f" Processor {processor.processor_name}"
        if processor.bin_size:
            table_title += f", {processor.bin_size} seconds"
    table = Table(title=table_title)
    table.add_column("Time", justify="left")
    table.add_column("Value", justify="right")
    table.add_column("Status", justify="right")
    table.add_column("Severity", justify="right")
    for e in events:
        table.add_row(str(e.pd_timestamp), str(e.val), str(e.status), str(e.severity))
    console.print(table)
    ctx.exit(0)
