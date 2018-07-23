# -*- coding: utf-8 -*-
"""Tests for epicsarchiver.utils module."""
import os
from datetime import datetime
from epicsarchiver import utils

SAMPLES_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), "samples")


def test_format_date():
    assert utils.format_date("20180715") == "2018-07-15T00:00:00.000000Z"
    assert utils.format_date("20180715 17:45") == "2018-07-15T17:45:00.000000Z"
    assert utils.format_date(datetime(2018, 7, 15, 19, 5)) == "2018-07-15T19:05:00.000000Z"


def test_parse_archive_file():
    filename = os.path.join(SAMPLES_PATH, "file1.archive")
    pvs = utils.parse_archive_file(filename, "1.0", "MONITOR")
    assert list(pvs) == [
        {
            "pv": "CrS-ACCP:CRYO-GT-34884:Val",
            "samplingperiod": "30",
            "samplingmethod": "MONITOR",
        },
        {
            "pv": "CrS-ACCP:CRYO-TT-31650:Val",
            "samplingperiod": "15.0",
            "samplingmethod": "SCAN",
        },
        {
            "pv": "CrS-ACCP:CRYO-TT-31355:Val",
            "samplingperiod": "86400",
            "samplingmethod": "MONITOR",
        },
        {
            "pv": "CrS-ACCP:CRYO-TT-31730:Val",
            "samplingperiod": "1.0",
            "samplingmethod": "MONITOR",
        },
    ]
