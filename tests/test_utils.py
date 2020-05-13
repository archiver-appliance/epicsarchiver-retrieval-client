# -*- coding: utf-8 -*-
"""Tests for epicsarchiver.utils module."""
import os
import pytest
from datetime import datetime
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
        utils.format_date(datetime(2018, 7, 15, 19, 5)) == "2018-07-15T19:05:00.000000Z"
    )


def test_parse_archive_file():
    filename = os.path.join(SAMPLES_PATH, "file1.archive")
    pvs = utils.parse_archive_file(filename)
    assert list(pvs) == FILE1_PVS


def test_parse_rename_file():
    filename = os.path.join(SAMPLES_PATH, "file1.rename")
    pvs = utils.parse_rename_file(filename)
    assert list(pvs) == FILE1_RENAME


def test_parse_rename_file_incomplete_line(capsys):
    filename = os.path.join(SAMPLES_PATH, "file2.rename")
    pvs = utils.parse_rename_file(filename)
    assert list(pvs) == FILE2_RENAME
    captured_stdout, captured_stderr = capsys.readouterr()
    assert "Skipping: CrS-TICP:Cryo-TE-33483:Val. Not enough values." in captured_stderr


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
    "input,expected",
    [({"status": "ok"}, True), ({"status": "foo"}, False), ({"hello": "world"}, False)],
)
def test_check_result(input, expected):
    output = utils.check_result(input)
    assert output is expected


@pytest.mark.parametrize(
    "input,default_message,output",
    [
        ({"status": "nok"}, "Not OK", "Not OK\n"),
        ({"validation": "Hello"}, None, "Hello\n"),
        ({"validation": "Hello"}, "foo", "Hello\n"),
    ],
)
def test_check_result_message(capsys, input, default_message, output):
    utils.check_result(input, default_message)
    captured_stdout, captured_stderr = capsys.readouterr()
    assert captured_stderr == output
