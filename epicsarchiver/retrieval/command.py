"""Command module."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Dict, List, Tuple

import click
from dateutil import tz
from pandas import Timestamp
from pytz import UTC
from rich.console import Console
from rich.table import Table

from epicsarchiver.common.command import handle_debug
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


AlignedPVEvents = List[Tuple[Timestamp, Dict[str, ArchiveEvent]]]


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
    console = Console()
    processor = (
        Processor(ProcessorName[processor_name.upper()], bin_size)
        if processor_name
        else None
    )
    LOG.debug("pvs %s", pvs)
    events: AlignedPVEvents = []
    if len(pvs) == 1:
        meta, events = asyncio.run(
            _single_fetch_events(archiver, pvs[0], start, end, processor=processor)
        )
    events = asyncio.run(
        _multi_fetch_events(archiver, list(pvs), start, end, processor=processor)
    )
    table_title = _table_title(pvs, start, end, processor)
    table_caption = _table_caption(_meta_field_values(meta) if meta else None)
    table = (
        _create_multi_table(pvs, table_title, events)
        if len(pvs) > 1
        else _create_singular_table(pvs[0], table_title, table_caption, events)
    )
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
    for e in events:
        event = e[1].get(pv)
        if event:
            table.add_row(
                _to_local_timestamp_str(e[0]),
                str(event.val),
                str(event.status),
                str(event.severity),
            )
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
