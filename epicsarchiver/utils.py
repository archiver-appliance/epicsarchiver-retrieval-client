# -*- coding: utf-8 -*-
"""Utility functions"""
import datetime
import itertools
from dateutil import parser


def format_date(date_or_str):
    """Return a string representing the date and time in ISO 8601 format

    :param date_or_str: can be a datetime object or string
                        if a string is given, it will be parsed automatically.
                        Timezone is ignored. UTC is always assumed.
    :return: string in ISO 8601 format
    """
    if not isinstance(date_or_str, datetime.datetime):
        dt = parser.parse(date_or_str, ignoretz=True)
    else:
        dt = date_or_str
    return dt.isoformat(timespec="microseconds") + "Z"


def parse_archive_file(filename):
    with open(filename, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or line == "":
                # Remove empty lines and lines that start with "#"
                continue
            values = line.split()
            pv = {"pv": values[0]}
            # Passing samplingmethod and samplingperiod via the API
            # overwrites what is defined in the site policies.py.
            # We don't want that.
            # But we allow to force the policy
            if len(values) > 1:
                pv["policy"] = values[1]
            yield pv


def get_pvs_from_files(files):
    """Return a list of PV (as dict) from a list of files"""
    return list(
        itertools.chain.from_iterable(
            [parse_archive_file(filename) for filename in files]
        )
    )
