"""Tests for write_events() export function."""

from __future__ import annotations

import csv
import io
import json

import polars as pl

from epicsarchiver.write.export_format import Format, write_events
from tests.retrieval.fake_data import make_archive_event


def _write(fmt: Format, n_events: int = 2) -> bytes:
    events = [make_archive_event(pv="MY:PV", val=float(i)) for i in range(n_events)]
    dest = io.BytesIO()
    write_events(dest, fmt, events=events, meta=None)
    return dest.getvalue()


# ── CSV ────────────────────────────────────────────────────────────────────


def test_write_events_csv_has_expected_columns() -> None:
    reader = csv.DictReader(io.StringIO(_write(Format.CSV).decode("utf-8")))
    assert reader.fieldnames is not None
    assert {"date", "pv", "val", "severity", "status"}.issubset(set(reader.fieldnames))


def test_write_events_csv_row_count() -> None:
    reader = csv.DictReader(io.StringIO(_write(Format.CSV, n_events=3).decode("utf-8")))
    assert len(list(reader)) == 3


def test_write_events_csv_pv_value() -> None:
    dest = io.BytesIO()
    write_events(dest, Format.CSV, events=[make_archive_event(pv="TEST:PV")], meta=None)
    rows = list(csv.DictReader(io.StringIO(dest.getvalue().decode("utf-8"))))
    assert rows[0]["pv"] == "TEST:PV"


def test_write_events_csv_empty_events() -> None:
    dest = io.BytesIO()
    write_events(dest, Format.CSV, events=[], meta=None)
    reader = csv.DictReader(io.StringIO(dest.getvalue().decode("utf-8")))
    assert list(reader) == []
    assert reader.fieldnames is not None


# ── JSON ───────────────────────────────────────────────────────────────────


def test_write_events_json_produces_valid_json() -> None:
    data = json.loads(_write(Format.JSON))
    assert isinstance(data, list)
    assert len(data) == 2


def test_write_events_json_has_pv_field() -> None:
    dest = io.BytesIO()
    write_events(dest, Format.JSON, events=[make_archive_event(pv="MY:PV")], meta=None)
    assert json.loads(dest.getvalue())[0]["pv"] == "MY:PV"


def test_write_events_json_empty_events() -> None:
    dest = io.BytesIO()
    write_events(dest, Format.JSON, events=[], meta=None)
    assert json.loads(dest.getvalue()) == []


# ── Arrow IPC ──────────────────────────────────────────────────────────────


def test_write_events_arrow_produces_valid_ipc() -> None:
    df = pl.read_ipc(io.BytesIO(_write(Format.ARROW)))
    assert df.shape[0] == 2
    assert "pv" in df.columns


def test_write_events_arrow_empty_events() -> None:
    dest = io.BytesIO()
    write_events(dest, Format.ARROW, events=[], meta=None)
    df = pl.read_ipc(io.BytesIO(dest.getvalue()))
    assert df.shape[0] == 0
    assert "pv" in df.columns


# ── Parquet ────────────────────────────────────────────────────────────────


def test_write_events_parquet_produces_valid_parquet() -> None:
    df = pl.read_parquet(io.BytesIO(_write(Format.PARQUET)))
    assert df.shape[0] == 2
    assert "pv" in df.columns


def test_write_events_parquet_empty_events() -> None:
    dest = io.BytesIO()
    write_events(dest, Format.PARQUET, events=[], meta=None)
    df = pl.read_parquet(io.BytesIO(dest.getvalue()))
    assert df.shape[0] == 0
    assert "pv" in df.columns
