"""Tests for Click commands in epicsarchiver.retrieval.command."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from epicsarchiver.common.errors import ArchiverError
from epicsarchiver.retrieval.command import get, search
from tests.retrieval.fake_data import make_archive_event

_MOCK_ARCHIVER = MagicMock(hostname="archiver.example.org", port=17668)
_START = "2024-01-01 00:00:00"
_END = "2024-01-02 00:00:00"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


# ── get ────────────────────────────────────────────────────────────────────


def test_get_displays_table_exits_0(runner: CliRunner) -> None:
    events = [make_archive_event("MY:PV"), make_archive_event("MY:PV", val=2)]
    with patch(
        "epicsarchiver.retrieval.command._fetch_events",
        new=AsyncMock(return_value=(None, events)),
    ):
        result = runner.invoke(
            get,
            ["--start", _START, "--end", _END, "MY:PV"],
            obj={"archiver": _MOCK_ARCHIVER},
        )
    assert result.exit_code == 0, result.output


def test_get_no_events_exits_0(runner: CliRunner) -> None:
    with patch(
        "epicsarchiver.retrieval.command._fetch_events",
        new=AsyncMock(return_value=(None, [])),
    ):
        result = runner.invoke(
            get,
            ["--start", _START, "--end", _END, "MY:PV"],
            obj={"archiver": _MOCK_ARCHIVER},
        )
    assert result.exit_code == 0


def test_get_archiver_error_exits_1(runner: CliRunner) -> None:
    with patch(
        "epicsarchiver.retrieval.command._fetch_events",
        new=AsyncMock(side_effect=ArchiverError("boom")),
    ):
        result = runner.invoke(
            get,
            ["--start", _START, "--end", _END, "MY:PV"],
            obj={"archiver": _MOCK_ARCHIVER},
        )
    assert result.exit_code == 1


# ── search ─────────────────────────────────────────────────────────────────


def test_search_displays_results_exits_0(runner: CliRunner) -> None:
    pvs = ["MY:PV:1", "MY:PV:2", "MY:PV:3"]
    with patch(
        "epicsarchiver.retrieval.command._pv_name_search",
        new=AsyncMock(return_value=pvs),
    ):
        result = runner.invoke(
            search,
            ["MY:PV:.*"],
            obj={"archiver": _MOCK_ARCHIVER},
        )
    assert result.exit_code == 0


def test_search_no_results_exits_0(runner: CliRunner) -> None:
    with patch(
        "epicsarchiver.retrieval.command._pv_name_search",
        new=AsyncMock(return_value=[]),
    ):
        result = runner.invoke(
            search,
            ["NOTHING:.*"],
            obj={"archiver": _MOCK_ARCHIVER},
        )
    assert result.exit_code == 0
