"""Command module."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import click
from dateutil import tz
from pandas import Timestamp
from pytz import UTC
from rich.console import Console
from rich.table import Table

from epicsarchiver.common.command import handle_debug
from epicsarchiver.common.errors import ArchiverError
from epicsarchiver.common.validation import ValidationError
from epicsarchiver.retrieval.archive_event import ArchiveEvent
from epicsarchiver.retrieval.archiver_retrieval.async_archiver_retrieval import (
    AsyncArchiverRetrieval,
)
from epicsarchiver.retrieval.archiver_retrieval.processor import (
    Processor,
    ProcessorName,
)

if TYPE_CHECKING:
    from epicsarchiver.epicsarchiver import ArchiverAppliance
    from epicsarchiver.retrieval.pb import ArchiveEventsMeta

LOG: logging.Logger = logging.getLogger(__name__)


DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S.%f",
]


AlignedPVEvents = list[tuple[Timestamp, dict[str, ArchiveEvent]]]


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
    "--bin_size",
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
    """Print out data from an archiver cluster.

    ARGUMENT pvs What pvs to get data of.

    Example usage:

    .. code-block:: console

        epicsarchiver --hostname archiver-01.example.com get PV_NAME1 PV_NAME2

    """
    archiver: ArchiverAppliance = ctx.obj["archiver"]
    processor = (
        Processor(ProcessorName[processor_name.upper()], bin_size)
        if processor_name
        else None
    )
    LOG.debug("PVs to fetch data from %s", pvs)
    events: AlignedPVEvents = []
    try:
        meta = None
        if len(pvs) == 1:
            meta, events = asyncio.run(
                _single_fetch_events(archiver, pvs[0], start, end, processor=processor)
            )
        else:
            events = asyncio.run(
                _multi_fetch_events(
                    archiver, list(pvs), start, end, processor=processor
                )
            )
    except ArchiverError as exc:
        LOG.error("Error fetching data from archiver: %s", str(exc))  # noqa: TRY400
        LOG.debug("Exception traceback", exc_info=exc)
        ctx.exit(1)
    except ValidationError as exc:
        LOG.error("Validation error: %s", str(exc))  # noqa: TRY400
        LOG.debug("Exception traceback", exc_info=exc)
        ctx.exit(1)

    if not events:
        LOG.info("No events found for the given time period and PVs.")
        ctx.exit(0)

    table_title = _table_title(pvs, start, end, processor)
    table_caption = _table_caption(_meta_field_values(meta) if meta else None)
    table = (
        _create_multi_table(pvs, table_title, events)
        if len(pvs) > 1
        else _create_singular_table(pvs[0], table_title, table_caption, events)
    )
    console = Console()
    console.print(table)
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
@click.argument("pvstrings", type=str, required=True, nargs=-1)
@click.pass_context
def search(  # noqa: PLR0917, PLR0913
    ctx: click.core.Context,
    pvstrings: tuple[str],
    start: datetime | None,
    end: datetime | None,
    limit: int,
    debug: bool,  # noqa: FBT001, ARG001
) -> None:
    """Search for PV names using glob search, case insensitive, multiple words.

    Optionally specify start and/or end times to only return PVs that recorded data in
    the specified time range.

    ARGUMENT pvstrings Multiple strings to search for, use glob search characters

    Example usage:

    .. code-block:: console

        epicsarchiver --hostname archiver-01.example.com search         \
        PBI-APTM02:Ctrl-ECAT-100:*Temp1[2-4]*   mbl*0[6-7]0*ambient*

        epicsarchiver --hostname archiver-01.example.com search         \
        PBI-APTM02:* -s "2026-01-06 02:50:00"

        epicsarchiver --hostname archiver-01.example.com search         \
        MBL*:RFS*:*TempAmbient -s "2026-01-05"  -e "2026-01-06"

    """
    archiver: ArchiverAppliance = ctx.obj["archiver"]
    LOG.debug("Search strings: %s", pvstrings)
    LOG.debug("Limit: %s", limit)
    LOG.debug("Start: %s", start)
    LOG.debug("End:   %s", end)
    try:
        pv_name_list = asyncio.run(
            _pv_name_search(
                archiver=archiver,
                pvstrings=pvstrings,
                start=start,
                end=end,
                limit=limit,
            )
        )
    except ArchiverError as exc:
        LOG.error("Error fetching data from archiver: %s", str(exc))  # noqa: TRY400
        LOG.debug("Exception traceback", exc_info=exc)
        ctx.exit(1)

    if not pv_name_list:
        LOG.info("No PVs found.")
        ctx.exit(0)

    table_title = _search_table_title(pv_name_list, start, end)
    table = _create_pv_name_table(pv_list=pv_name_list, title=table_title)

    console = Console()
    console.print(table)

    ctx.exit(0)


def _meta_field_values(meta: dict[int, ArchiveEventsMeta]) -> dict[int, dict[str, str]]:
    return {
        year: {
            field.name: field.value or ""
            for field in field_values_dict.headers
            if field.name
        }
        for year, field_values_dict in meta.items()
    }


def _table_caption(
    field_values: dict[int, dict[str, str]] | None,
) -> str | None:
    if field_values:
        caption = ""
        for year, field_values_dict in field_values.items():
            caption += f"Field Values {year}\n"
            caption += "\n".join(
                f"{key}: {value}" for key, value in field_values_dict.items()
            )
        return caption
    return None


def _search_table_title(
    pvs: list[str],
    start: datetime | None,
    end: datetime | None,
) -> str:
    table_title = "Found " + str(len(pvs)) + " PV"
    if len(pvs) > 1:
        table_title += "s"
    if start and end:
        table_title += f"\nbetween {start} \n    and {end}"
    elif start:
        table_title += f"\nfrom {start} until now"
    elif end:
        table_title += f"\nbefore {end}"
    return table_title


def _table_title(
    pvs: tuple[str],
    start: datetime,
    end: datetime,
    processor: Processor | None,
) -> str:
    table_title = f"Period {start} - {end}"
    if len(pvs) == 1:
        table_title = pvs[0] + table_title
    if processor:
        table_title += f" Processor {processor.processor_name}"
        if processor.bin_size:
            table_title += f", {processor.bin_size} seconds"
    return table_title


def _create_multi_table(
    pvs: tuple[str],
    title: str,
    events: AlignedPVEvents,
) -> Table:
    table = Table(title=title)
    table.add_column("Time", justify="left")
    for pv in pvs:
        table.add_column(pv + " Value", justify="right")
    for e in events:
        table.add_row(
            _to_local_timestamp_str(e[0]),
            *[_val_to_str(e[1].get(pv)) for pv in pvs],
        )
    return table


def _to_local_timestamp_str(timestamp: Timestamp) -> str:
    return str(timestamp.tz_convert(tz.tzlocal()))


def _val_to_str(event: ArchiveEvent | None) -> str:
    if event:
        return str(event.val)
    return ""


def _create_singular_table(
    pv: str,
    title: str,
    caption: str | None,
    events: AlignedPVEvents,
) -> Table:
    table = Table(title=title, caption=caption, caption_justify="left")
    table.add_column("Time", justify="left")
    table.add_column("Value", justify="right")
    table.add_column("Status", justify="right")
    table.add_column("Severity", justify="right")
    for time_event in events:
        event = time_event[1].get(pv)
        if event:
            table.add_row(
                _to_local_timestamp_str(time_event[0]),
                str(event.val),
                str(event.status),
                str(event.severity),
            )
    return table


def _create_pv_name_table(
    pv_list: list[str],
    title: str,
) -> Table:
    table = Table(title=title)
    table.add_column("PV name", justify="left")
    for pv in pv_list:
        table.add_row(pv)
    return table


def filtered_event_field_values(fields: list[str], event: ArchiveEvent) -> list[str]:
    """Provide a list of field values for the given event.

    Args:
        fields (list[str]): Input field names to filter
        event (ArchiveEvent): Event to filter

    Returns:
        list[str]: Field values for the given event
    """
    LOG.debug("fields %s", event.field_values_dict)
    return [str(event.field_values_dict.get(field, "")) for field in fields]


def _align_events(
    all_events: dict[str, list[ArchiveEvent]],
) -> AlignedPVEvents:
    """Align events from multiple PVs by timestamp.

    Args:
        all_events (dict[str, list[ArchiveEvent]]): Events per PV with PV name as key

    Returns:
        AlignedPVEvents: List of pairs, (timestamp, dict[pv_name, pv_value])
    """
    data: dict[Timestamp, dict[str, ArchiveEvent]] = {}
    for pv, events in all_events.items():
        for event in events:
            if event.pd_timestamp not in data:
                data[event.pd_timestamp] = {}
            data[event.pd_timestamp][pv] = event

    return [(timestamp, data[timestamp]) for timestamp in sorted(data.keys())]


async def _multi_fetch_events(
    archiver: ArchiverAppliance,
    pvs: list[str],
    start: datetime,
    end: datetime,
    processor: Processor | None,
) -> AlignedPVEvents:
    async with AsyncArchiverRetrieval(archiver.hostname, archiver.port) as a_retrieval:
        all_events = await a_retrieval.get_all_events(
            set(pvs), start, end, processor=processor
        )
        return _align_events(all_events)


async def _single_fetch_events(
    archiver: ArchiverAppliance,
    pv: str,
    start: datetime,
    end: datetime,
    processor: Processor | None,
) -> tuple[dict[int, ArchiveEventsMeta], AlignedPVEvents]:
    async with AsyncArchiverRetrieval(archiver.hostname, archiver.port) as a_retrieval:
        meta, events = await a_retrieval.get_archive_data(
            pv, start, end, processor=processor
        )
        return meta, _align_events({pv: events})


async def _pv_name_search(
    archiver: ArchiverAppliance,
    pvstrings: tuple[str],
    start: datetime | None,
    end: datetime | None,
    limit: int,
) -> list[str]:
    async with AsyncArchiverRetrieval(archiver.hostname, archiver.port) as a_retrieval:
        return await a_retrieval.search(
            pvstrings=pvstrings, start=start, end=end, limit=limit
        )
