"""Tests for SearchTable terminal formatter."""

from __future__ import annotations

from datetime import datetime

from pytz import UTC
from rich.table import Table

from epicsarchiver.write.search_format import SearchTable

_START = datetime(2024, 1, 1, tzinfo=UTC)
_END = datetime(2024, 1, 2, tzinfo=UTC)
_PVS = ["PV1", "PV2", "PV3"]


# ── _search_table_title ────────────────────────────────────────────────────


def test_title_no_time_range() -> None:
    title = SearchTable(pvs=_PVS, start=None, end=None)._search_table_title()
    assert "Found 3 PVs" in title
    assert "between" not in title
    assert "until now" not in title
    assert "before" not in title


def test_title_singular_pv() -> None:
    title = SearchTable(pvs=["ONLY:PV"], start=None, end=None)._search_table_title()
    assert "Found 1 PV" in title
    assert "PVs" not in title


def test_title_start_only() -> None:
    title = SearchTable(pvs=_PVS, start=_START, end=None)._search_table_title()
    assert "until now" in title
    assert "before" not in title
    assert "between" not in title


def test_title_end_only() -> None:
    title = SearchTable(pvs=_PVS, start=None, end=_END)._search_table_title()
    assert "before" in title
    assert "until now" not in title
    assert "between" not in title


def test_title_start_and_end() -> None:
    title = SearchTable(pvs=_PVS, start=_START, end=_END)._search_table_title()
    assert "between" in title
    assert "until now" not in title
    assert "before" not in title


# ── render ───────────────────────────────────────────────────────────


def test_render_returns_rich_table() -> None:
    assert isinstance(SearchTable(pvs=_PVS, start=None, end=None).render(), Table)


def test_render_row_count_matches_pvs() -> None:
    table = SearchTable(pvs=_PVS, start=None, end=None).render()
    assert table.row_count == len(_PVS)


def test_render_empty_pvs() -> None:
    table = SearchTable(pvs=[], start=None, end=None).render()
    assert table.row_count == 0
