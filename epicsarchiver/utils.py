# -*- coding: utf-8 -*-
"""Utility functions"""
import datetime
import itertools
import sys
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


def parse_archive_file(filename, appliance=None):
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
            if appliance:
                pv["appliance"] = appliance
            yield pv


def parse_rename_file(filename):
    with open(filename, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or line == "":
                # Remove empty lines and lines that start with "#"
                continue
            values = line.split()
            if len(values) >= 2:
                yield tuple(values[:2])
            else:
                sys.stderr.write(f"Skipping: {line}. Not enough values.\n")


def get_pvs_from_files(files, appliance=None):
    """Return a list of PV (as dict) from a list of files"""
    return list(
        itertools.chain.from_iterable(
            [parse_archive_file(filename, appliance) for filename in files]
        )
    )


def get_rename_pvs_from_files(files):
    """Return a list of (current, new) PV names from a list of files"""
    return list(
        itertools.chain.from_iterable(
            [parse_rename_file(filename) for filename in files]
        )
    )


def check_result(result, default_message=None):
    """Check a result returned by the Archiver Appliance

    Return True if the status is ok
    Return False otherwise and print the default_message or validation value
    """
    status = result.get("status", "nok")
    if status.lower() != "ok":
        message = result.get("validation", default_message)
        sys.stderr.write(f"{message}\n")
        return False
    return True
