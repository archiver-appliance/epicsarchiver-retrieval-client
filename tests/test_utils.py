"""Tests for epicsarchiver.utils module."""
import logging
import os
from datetime import datetime

import pytest
from pytz import UTC

from epicsarchiver import utils

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


def test_format_date():
    assert utils.format_date("20180715") == "2018-07-15T00:00:00.000000Z"
    assert utils.format_date("20180715 17:45") == "2018-07-15T17:45:00.000000Z"
    assert (
        utils.format_date(datetime(2018, 7, 15, 19, 5, tzinfo=UTC))
        == "2018-07-15T19:05:00.000000Z"
    )


def test_parse_archive_file():
    filename = os.path.join(SAMPLES_PATH, "file1.archive")
    pvs = utils.parse_archive_file(filename)
    assert list(pvs) == FILE1_PVS


def test_parse_rename_file():
    filename = os.path.join(SAMPLES_PATH, "file1.rename")
    pvs = utils.parse_rename_file(filename)
    assert list(pvs) == FILE1_RENAME


def test_parse_rename_file_incomplete_line(caplog):
    filename = os.path.join(SAMPLES_PATH, "file2.rename")
    with caplog.at_level(logging.ERROR):
        pvs = utils.parse_rename_file(filename)
    assert list(pvs) == FILE2_RENAME
    captured_log = caplog.text
    assert (
        "Skipping: CrS-TICP:Cryo-TE-33483:Val. Invalid format, must be OLDNAME NEWNAME."
        in captured_log
    )


def test_get_pvs_from_files():
    files = [
        os.path.join(SAMPLES_PATH, "file1.archive"),
        os.path.join(SAMPLES_PATH, "file2.archive"),
    ]
    pvs = utils.get_pvs_from_files(files)
    assert pvs == FILE1_PVS + FILE2_PVS


def test_get_pvs_from_files_with_appliance():
    files = [os.path.join(SAMPLES_PATH, "file2.archive")]
    pvs = utils.get_pvs_from_files(files, appliance="appliance0")
    assert pvs == FILE2_PVS_APPLIANCE


def test_get_rename_pvs_from_files():
    files = [
        os.path.join(SAMPLES_PATH, "file1.rename"),
        os.path.join(SAMPLES_PATH, "file2.rename"),
    ]
    pvs = utils.get_rename_pvs_from_files(files)
    assert pvs == FILE1_RENAME + FILE2_RENAME


@pytest.mark.parametrize(
    "test_input,expected",
    [({"status": "ok"}, True), ({"status": "foo"}, False), ({"hello": "world"}, False)],
)
def test_check_result(test_input, expected):
    output = utils.check_result(test_input)
    assert output is expected


@pytest.mark.parametrize(
    "test_input,default_message,output",
    [
        ({"status": "nok"}, "Not OK", "Not OK\n"),
        ({"validation": "Hello"}, None, "Hello\n"),
        ({"validation": "Hello"}, "foo", "Hello\n"),
    ],
)
def test_check_result_message(caplog, test_input, default_message, output):
    with caplog.at_level(logging.ERROR):
        utils.check_result(test_input, default_message)
    captured_log = caplog.text
    assert output in captured_log
