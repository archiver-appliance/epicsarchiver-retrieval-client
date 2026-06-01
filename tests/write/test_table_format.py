"""Tests for FormatTable terminal formatter."""

from __future__ import annotations

from datetime import datetime

from pytz import UTC
from rich.table import Table

from epicsarchiver.retrieval.archive_event import (
    ArchiveEvent,
    ArchiveEventsMeta,
    FieldValue,
)
from epicsarchiver.retrieval.client.processor import (
    Processor,
    ProcessorName,
)
from epicsarchiver.write.table_format import FormatTable
from tests.retrieval.fake_data import make_archive_event

_START = datetime(2024, 1, 1, tzinfo=UTC)
_END = datetime(2024, 1, 2, tzinfo=UTC)


def _ft(
    events: list[ArchiveEvent] | None = None,
    pvs: tuple[str, ...] = ("TEST:PV",),
    processor: Processor | None = None,
    meta: dict[int, ArchiveEventsMeta] | None = None,
) -> FormatTable:
    if events is None:
        events = [make_archive_event()]
    return FormatTable(
        events=events, pvs=pvs, start=_START, end=_END, processor=processor, meta=meta
    )


class TestTableTitle:
    def test_single_pv_starts_with_pv_name(self) -> None:
        title = _ft(pvs=("MY:PV",))._table_title()
        assert title.startswith("MY:PV")

    def test_multiple_pvs_omits_pv_names(self) -> None:
        title = _ft(pvs=("PV1", "PV2"))._table_title()
        assert "PV1" not in title
        assert "PV2" not in title
        assert "Period" in title

    def test_contains_start_and_end(self) -> None:
        title = _ft()._table_title()
        assert str(_START) in title
        assert str(_END) in title

    def test_with_processor_includes_name(self) -> None:
        proc = Processor(ProcessorName.MEAN, 60)
        title = _ft(processor=proc)._table_title()
        assert "mean" in title.lower()
        assert "60" in title

    def test_processor_without_bin_size(self) -> None:
        proc = Processor(ProcessorName.LASTSAMPLE, None)
        title = _ft(processor=proc)._table_title()
        assert "lastsample" in title.lower()


class TestTableCaption:
    def test_none_when_empty(self) -> None:
        assert FormatTable._table_caption({}) is None

    def test_contains_year(self) -> None:
        caption = FormatTable._table_caption({2024: {"EGU": "degC"}})
        assert caption is not None
        assert "2024" in caption

    def test_contains_field_key_value(self) -> None:
        caption = FormatTable._table_caption({
            2024: {"EGU": "degC", "DESC": "temperature"}
        })
        assert caption is not None
        assert "EGU: degC" in caption
        assert "DESC: temperature" in caption

    def test_multiple_years(self) -> None:
        caption = FormatTable._table_caption({2023: {"A": "1"}, 2024: {"B": "2"}})
        assert caption is not None
        assert "2023" in caption
        assert "2024" in caption


class TestMetaFieldValues:
    def test_none_meta_returns_empty(self) -> None:
        assert _ft(meta=None)._meta_field_values() == {}

    def test_extracts_by_year(self) -> None:
        meta = {
            2024: ArchiveEventsMeta(
                pv_name="PV",
                pv_type="t",
                element_count=1,
                headers=[FieldValue(name="EGU", value="mm")],
                year=2024,
            )
        }
        result = _ft(meta=meta)._meta_field_values()
        assert result == {2024: {"EGU": "mm"}}


class TestTableFormatRender:
    def test_returns_rich_table(self) -> None:
        assert isinstance(_ft().render(), Table)

    def test_has_five_columns(self) -> None:
        table = _ft().render()
        assert len(table.columns) == 5

    def test_row_count_matches_events(self) -> None:
        events = [
            make_archive_event(),
            make_archive_event(val=2),
            make_archive_event(val=3),
        ]
        table = _ft(events=events).render()
        assert table.row_count == 3

    def test_empty_events_gives_zero_rows(self) -> None:
        table = _ft(events=[]).render()
        assert table.row_count == 0
