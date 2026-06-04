"""Command module."""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import click
from pytz import UTC

from epicsarchiver.common.command import handle_debug
from epicsarchiver.common.errors import ArchiverError
from epicsarchiver.common.validation import ValidationError
from epicsarchiver.retrieval.archive_event import ArchiveEvent
from epicsarchiver.retrieval.client.async_archiver_retrieval import (
    AsyncArchiverRetrieval,
)
from epicsarchiver.retrieval.client.processor import (
    Processor,
    ProcessorName,
)
from epicsarchiver.retrieval.pb import parse_pb_data, read_pb_file
from epicsarchiver.write.export_format import Format, write_events
from epicsarchiver.write.search_format import SearchTable
from epicsarchiver.write.table_format import FormatTable

if TYPE_CHECKING:
    from epicsarchiver.epicsarchiver import ArchiverAppliance
    from epicsarchiver.retrieval.archive_event import ArchiveEvent, ArchiveEventsMeta

LOG: logging.Logger = logging.getLogger(__name__)


DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S.%f",
]


@click.command(context_settings={"show_default": True})
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
    show_default=False,
    help="Start time of query [default: 30 seconds ago]",
)
@click.option(
    "--end",
    "-e",
    default=str(datetime.now(tz=UTC).strftime(DATE_FORMATS[2])),
    type=click.DateTime(formats=DATE_FORMATS),
    show_default=False,
    help="End time of query, [default: now]",
)
@click.option(
    "--processor-name",
    "-p",
    type=click.Choice(
        [processor.name for processor in ProcessorName], case_sensitive=False
    ),
    help="""PreProcessor to use

        \b
        Docs at https://epicsarchiver.readthedocs.io/en/latest/user/userguide.html#processing-of-data
    """,
)
@click.option(
    "--bin-size",
    "-b",
    type=int,
    help="Bin size (mostly in seconds) for preprocessor.",
)
@click.argument("pvs", type=str, required=True, nargs=-1)
@click.pass_context
def get(  # noqa: PLR0917, PLR0913
    ctx: click.core.Context,
    pvs: tuple[str],
    start: datetime,
    end: datetime,
    processor_name: str | None,
    bin_size: int | None,
    debug: bool,  # noqa: FBT001, ARG001
) -> None:
    """Print out data from an archiver cluster as a table.

    ARGUMENT pvs What pvs to get data of.

    Example usage:

    .. code-block:: console

        arch-retrieval --hostname archiver-01.example.com get PV_NAME1 PV_NAME2

    """
    archiver: ArchiverAppliance = ctx.obj["archiver"]
    processor = (
        Processor(ProcessorName[processor_name.upper()], bin_size)
        if processor_name
        else None
    )
    LOG.debug("PVs to fetch data from %s", pvs)
    try:
        meta, events = asyncio.run(
            _fetch_events(archiver, pvs, start, end, processor=processor)
        )
    except ArchiverError as exc:
        LOG.error("Error fetching data from archiver: %s", exc)  # noqa: TRY400
        LOG.debug("Exception traceback", exc_info=exc)
        ctx.exit(1)
        return
    except ValidationError as exc:
        LOG.error("Validation error: %s", exc)  # noqa: TRY400
        LOG.debug("Exception traceback", exc_info=exc)
        ctx.exit(1)
        return

    if not events:
        LOG.info("No events found for the given time period and PVs.")
        ctx.exit(0)
        return

    FormatTable(
        events=events,
        pvs=pvs,
        start=start,
        end=end,
        processor=processor,
        meta=meta,
    ).write()
    ctx.exit(0)


@click.command(context_settings={"show_default": True})
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
    show_default=False,
    help="Start time of query [default: 30 seconds ago]",
)
@click.option(
    "--end",
    "-e",
    default=str(datetime.now(tz=UTC).strftime(DATE_FORMATS[2])),
    type=click.DateTime(formats=DATE_FORMATS),
    show_default=False,
    help="End time of query, [default: now]",
)
@click.option(
    "--processor-name",
    "-p",
    type=click.Choice(
        [processor.name for processor in ProcessorName], case_sensitive=False
    ),
    help="PreProcessor to use.",
)
@click.option(
    "--bin-size",
    "-b",
    type=int,
    help="Bin size (mostly in seconds) for preprocessor.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice([f.name for f in Format], case_sensitive=False),
    default=Format.JSON.name,
    show_default=True,
    help="Output format, written to stdout.",
)
@click.argument("pv", type=str, required=True)
@click.pass_context
def export(  # noqa: PLR0917, PLR0913
    ctx: click.core.Context,
    pv: str,
    start: datetime,
    end: datetime,
    processor_name: str | None,
    bin_size: int | None,
    output_format: str,
    debug: bool,  # noqa: FBT001, ARG001
) -> None:
    """Export PV data to stdout in a machine-readable format.

    ARGUMENT pv PV name to export data for.

    Example usage:

    .. code-block:: console

        arch-retrieval --hostname archiver.example.com export --format json MY_PV
        arch-retrieval --hostname archiver.example.com export --format pb MY_PV > out.pb

    Raises:
        UsageError: When a polars-backed format is requested without the [polars] extra.

    """
    archiver: ArchiverAppliance = ctx.obj["archiver"]
    fmt = Format[output_format.upper()]
    processor = (
        Processor(ProcessorName[processor_name.upper()], bin_size)
        if processor_name
        else None
    )
    try:
        raw_bytes = asyncio.run(
            _fetch_raw_pb(
                archiver,
                pv,
                start,
                end,
                processor=processor,
                fetch_latest_metadata=(fmt != Format.PB),
            )
        )
    except ArchiverError as exc:
        LOG.error("Error fetching data from archiver: %s", exc)  # noqa: TRY400
        LOG.debug("Exception traceback", exc_info=exc)
        ctx.exit(1)
        return

    if not raw_bytes:
        LOG.info("No data returned for %s", pv)
        ctx.exit(0)
        return

    if fmt is Format.PB:
        sys.stdout.buffer.write(raw_bytes)
    else:
        meta, events = parse_pb_data(raw_bytes)
        try:
            write_events(sys.stdout.buffer, fmt, events=events, meta=meta)
        except ImportError as err:
            msg = (
                f"--format {fmt.name} requires the [polars] extra: "
                "pip install epicsarchiver-retrieval-client[polars]"
            )
            raise click.UsageError(msg) from err

    ctx.exit(0)


@click.command()
@click.option(
    "--debug",
    is_flag=True,
    callback=handle_debug,
    help="Turn on debug logging",
)
@click.argument("file", type=click.Path(exists=True, dir_okay=False, readable=True))
@click.pass_context
def read_pb(
    ctx: click.core.Context,
    file: str,
    debug: bool,  # noqa: FBT001, ARG001
) -> None:
    r"""Display events from a local PB file.

    ARGUMENT file Path to the .pb file to read.

    Example usage:

    .. code-block:: console

        arch-retrieval read-pb MY_PV_2026.pb

    """
    meta, events = read_pb_file(file)

    if not events:
        LOG.info("No events found in %s", file)
        ctx.exit(0)
        return

    FormatTable(
        events=events,
        pvs=(events[0].pv,),
        start=events[0].timestamp,
        end=events[-1].timestamp,
        processor=None,
        meta=meta,
    ).write()
    ctx.exit(0)


@click.command(context_settings={"show_default": True})
@click.option(
    "--start",
    "-s",
    default=None,
    type=click.DateTime(formats=DATE_FORMATS),
    help="Start time of query",
)
@click.option(
    "--end",
    "-e",
    default=None,
    type=click.DateTime(formats=DATE_FORMATS),
    help="End time of query",
)
@click.option(
    "--limit",
    "-l",
    default=500,
    type=int,
    help="Limit of PV names to return for each search string given. "
    "To get all the PV names, (potentially in the millions), set limit to -1.",
)
@click.option(
    "--debug",
    is_flag=True,
    callback=handle_debug,
    help="Turn on debug logging",
)
@click.argument("query", type=str, required=True, nargs=1)
@click.pass_context
def search(  # noqa: PLR0917, PLR0913
    ctx: click.core.Context,
    query: str,
    start: datetime | None,
    end: datetime | None,
    limit: int,
    debug: bool,  # noqa: FBT001, ARG001
) -> None:
    """Search for PV names using regex search patterns.

    Optionally specify start and/or end times to only return PVs that recorded data in
    the specified time range.

    ARGUMENT query PV name regex search pattern.

    Example usage:

    .. code-block:: console

        arch-retrieval --hostname archiver-01.example.com search         \
        "PBI-APTM02:Ctrl-ECAT-100:.*Temp1[2-4].*"

        arch-retrieval --hostname archiver-01.example.com search         \
        "PBI-APTM02:.*" -s "2026-01-06 02:50:00"

        arch-retrieval --hostname archiver-01.example.com search         \
        "(?i)mbl-060RFC:.*:tempambient" -s "2026-01-05"  -e "2026-01-06"

    """
    archiver: ArchiverAppliance = ctx.obj["archiver"]
    try:
        pv_name_list = asyncio.run(
            _pv_name_search(
                archiver=archiver,
                query=query,
                start=start,
                end=end,
                limit=limit,
            )
        )
    except ArchiverError:
        LOG.exception("Error fetching data from archiver")
        ctx.exit(1)
        return

    if not pv_name_list:
        LOG.info("No PVs found.")
        ctx.exit(0)
        return

    SearchTable(pvs=pv_name_list, start=start, end=end).write()
    ctx.exit(0)


async def _fetch_events(
    archiver: ArchiverAppliance,
    pvs: tuple[str, ...],
    start: datetime,
    end: datetime,
    processor: Processor | None,
) -> tuple[dict[int, ArchiveEventsMeta] | None, list[ArchiveEvent]]:
    async with AsyncArchiverRetrieval(archiver.hostname, archiver.port) as a_retrieval:
        if len(pvs) == 1:
            return await a_retrieval.get_archive_data(
                pvs[0], start, end, processor=processor
            )
        all_events = await a_retrieval.get_all_events(
            set(pvs), start, end, processor=processor
        )
        events = sorted(
            (e for pv_events in all_events.values() for e in pv_events),
            key=lambda e: e.timestamp_ns,
        )
        return None, events


async def _pv_name_search(
    archiver: ArchiverAppliance,
    query: str,
    start: datetime | None,
    end: datetime | None,
    limit: int,
) -> list[str]:
    async with AsyncArchiverRetrieval(archiver.hostname, archiver.port) as a_retrieval:
        return await a_retrieval.search(query=query, start=start, end=end, limit=limit)


async def _fetch_raw_pb(  # noqa: PLR0913, PLR0917
    archiver: ArchiverAppliance,
    pv: str,
    start: datetime,
    end: datetime,
    processor: Processor | None = None,
    fetch_latest_metadata: bool = True,  # noqa: FBT001, FBT002
) -> bytes:
    pv_request = processor.calc_pv_name(pv) if processor else pv
    async with AsyncArchiverRetrieval(archiver.hostname, archiver.port) as a_retrieval:
        response = await a_retrieval.get_data_raw(
            pv_request, start, end, fetch_latest_metadata=fetch_latest_metadata
        )
        return await response.content.read()
