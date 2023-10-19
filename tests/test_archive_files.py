import logging
import os
from pathlib import Path

import pytest

from epicsarchiver import archive_files

SAMPLES_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), "samples")
FILE1_PVS = [
    {"pv": "CrS-ACCP:CRYO-GT-34884:Val"},
    {"pv": "CrS-ACCP:CRYO-TT-31650:Val", "policy": "slow"},
    {"pv": "CrS-ACCP:CRYO-TT-31355:Val", "policy": "default"},
    {"pv": "CrS-ACCP:CRYO-TT-31730:Val"},
]
FILE2_PVS = [
    {"pv": "CrS-TICP:Cryo-TE-31459B:Val"},
    {"pv": "CrS-TICP:Cryo-TE-33483:Val", "policy": "slow"},
]
FILE2_PVS_APPLIANCE = [
    {"pv": "CrS-TICP:Cryo-TE-31459B:Val", "appliance": "appliance0"},
    {"pv": "CrS-TICP:Cryo-TE-33483:Val", "policy": "slow", "appliance": "appliance0"},
]
FILE1_RENAME = [
    ("CrS-TICP:Cryo-TE-31459B:Val", "CrS-TICP:Cryo-TE-31459C:Val"),
    ("CrS-TICP:Cryo-TE-33483:Val", "CrS-TICP:Cryo-TE-33484:Val"),
]
FILE2_RENAME = [
    ("CrS-ACCP:CRYO-GT-34884:Val", "CrS-ACCP:CRYO-GT-34884B:Val"),
]


def test_parse_archive_file() -> None:
    filename = Path(os.path.join(SAMPLES_PATH, "file1.archive"))
    pvs = archive_files.parse_archive_file(filename)
    assert list(pvs) == FILE1_PVS


def test_parse_rename_file() -> None:
    filename = Path(os.path.join(SAMPLES_PATH, "file1.rename"))
    pvs = archive_files.parse_rename_file(filename)
    assert list(pvs) == FILE1_RENAME


def test_parse_rename_file_incomplete_line(caplog: pytest.LogCaptureFixture) -> None:
    filename = Path(os.path.join(SAMPLES_PATH, "file2.rename"))
    with caplog.at_level(logging.ERROR):
        pvs = archive_files.parse_rename_file(filename)
    assert list(pvs) == FILE2_RENAME
    captured_log = caplog.text
    assert (
        "Skipping: CrS-TICP:Cryo-TE-33483:Val. Invalid format, must be OLDNAME NEWNAME."
        in captured_log
    )


def test_get_pvs_from_files() -> None:
    files = [
        Path(os.path.join(SAMPLES_PATH, "file1.archive")),
        Path(os.path.join(SAMPLES_PATH, "file2.archive")),
    ]
    pvs = archive_files.get_pvs_from_files(files)
    assert pvs == FILE1_PVS + FILE2_PVS


def test_get_pvs_from_files_with_appliance() -> None:
    files = [Path(os.path.join(SAMPLES_PATH, "file2.archive"))]
    pvs = archive_files.get_pvs_from_files(files, appliance="appliance0")
    assert pvs == FILE2_PVS_APPLIANCE


def test_get_rename_pvs_from_files() -> None:
    files = [
        os.path.join(SAMPLES_PATH, "file1.rename"),
        os.path.join(SAMPLES_PATH, "file2.rename"),
    ]
    pvs = archive_files.get_rename_pvs_from_files(files)
    assert pvs == FILE1_RENAME + FILE2_RENAME
