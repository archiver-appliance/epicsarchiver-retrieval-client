"""Tests for Click commands in epicsarchiver.retrieval.command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from epicsarchiver.common.errors import ArchiverError
from epicsarchiver.retrieval import EPICSEvent_pb2 as ee
from epicsarchiver.retrieval.command import export, get, read_pb, search
from tests.retrieval.fake_data import TEST_EVENTS, create_pb_bytes, make_archive_event

_SAMPLES = Path(__file__).parent / "samples"
_SIGMA_PB = _SAMPLES / "sigma_test_pb.pb"

_MOCK_ARCHIVER = MagicMock(hostname="archiver.example.org", port=17668)
_START = "2024-01-01 00:00:00"
_END = "2024-01-02 00:00:00"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def pb_bytes() -> bytes:
    info = ee.PayloadInfo(type=ee.SCALAR_INT, pvname="MY:PV", year=2018)
    return create_pb_bytes(TEST_EVENTS, info)


class TestReadPb:
    def test_sigma_sample_exits_0(self, runner: CliRunner) -> None:
        result = runner.invoke(read_pb, [str(_SIGMA_PB)], obj={})
        assert result.exit_code == 0, result.output

    def test_no_events_exits_0(self, runner: CliRunner, tmp_path: Path) -> None:
        empty_pb = tmp_path / "empty.pb"
        info = ee.PayloadInfo(type=ee.SCALAR_INT, pvname="EMPTY:PV", year=2024)
        empty_pb.write_bytes(create_pb_bytes([], info))
        with patch(
            "epicsarchiver.retrieval.command.read_pb_file", return_value=({}, [])
        ):
            result = runner.invoke(read_pb, [str(empty_pb)], obj={})
        assert result.exit_code == 0


class TestGet:
    def test_displays_table_exits_0(self, runner: CliRunner) -> None:
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

    def test_no_events_exits_0(self, runner: CliRunner) -> None:
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

    def test_get_archiver_error_exits_1(self, runner: CliRunner) -> None:
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


class TestSearch:
    def test_displays_results_exits_0(self, runner: CliRunner) -> None:
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

    def test_no_results_exits_0(self, runner: CliRunner) -> None:
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


class TestExport:
    def test_json_exits_0(self, runner: CliRunner, pb_bytes: bytes) -> None:
        with patch(
            "epicsarchiver.retrieval.command._fetch_raw_pb",
            new=AsyncMock(return_value=pb_bytes),
        ):
            result = runner.invoke(
                export,
                ["--format", "json", "--start", _START, "--end", _END, "MY:PV"],
                obj={"archiver": _MOCK_ARCHIVER},
            )
        assert result.exit_code == 0, result.output

    def test_csv_exits_0(self, runner: CliRunner, pb_bytes: bytes) -> None:
        with patch(
            "epicsarchiver.retrieval.command._fetch_raw_pb",
            new=AsyncMock(return_value=pb_bytes),
        ):
            result = runner.invoke(
                export,
                ["--format", "csv", "--start", _START, "--end", _END, "MY:PV"],
                obj={"archiver": _MOCK_ARCHIVER},
            )
        assert result.exit_code == 0, result.output

    def test_pb_exits_0(self, runner: CliRunner, pb_bytes: bytes) -> None:
        with patch(
            "epicsarchiver.retrieval.command._fetch_raw_pb",
            new=AsyncMock(return_value=pb_bytes),
        ):
            result = runner.invoke(
                export,
                ["--format", "pb", "--start", _START, "--end", _END, "MY:PV"],
                obj={"archiver": _MOCK_ARCHIVER},
            )
        assert result.exit_code == 0, result.output

    def test_no_data_exits_0(self, runner: CliRunner) -> None:
        with patch(
            "epicsarchiver.retrieval.command._fetch_raw_pb",
            new=AsyncMock(return_value=b""),
        ):
            result = runner.invoke(
                export,
                ["--start", _START, "--end", _END, "MY:PV"],
                obj={"archiver": _MOCK_ARCHIVER},
            )
        assert result.exit_code == 0

    def test_parquet_exits_0(self, runner: CliRunner, pb_bytes: bytes) -> None:
        with patch(
            "epicsarchiver.retrieval.command._fetch_raw_pb",
            new=AsyncMock(return_value=pb_bytes),
        ):
            result = runner.invoke(
                export,
                ["--format", "parquet", "--start", _START, "--end", _END, "MY:PV"],
                obj={"archiver": _MOCK_ARCHIVER},
            )
        assert result.exit_code == 0, result.output

    def test_archiver_error_exits_1(self, runner: CliRunner) -> None:
        with patch(
            "epicsarchiver.retrieval.command._fetch_raw_pb",
            new=AsyncMock(side_effect=ArchiverError("boom")),
        ):
            result = runner.invoke(
                export,
                ["--start", _START, "--end", _END, "MY:PV"],
                obj={"archiver": _MOCK_ARCHIVER},
            )
        assert result.exit_code == 1
