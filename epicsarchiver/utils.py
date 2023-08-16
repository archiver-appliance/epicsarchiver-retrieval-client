"""Utility functions"""
import datetime
import itertools
import logging
from collections.abc import Generator
from typing import Any

from dateutil import parser

LOG: logging.Logger = logging.getLogger(__name__)


def format_date(date_or_str: datetime.datetime | str) -> str:
    """Return a string representing the date and time in ISO 8601 format

    :param date_or_str: can be a datetime object or string
                        if a string is given, it will be parsed automatically.
                        Timezone is ignored. UTC is always assumed.
    :return: string in ISO 8601 format
    """
    if not isinstance(date_or_str, datetime.datetime):
        dt = parser.parse(date_or_str, ignoretz=True)
    else:
        dt = date_or_str.replace(tzinfo=None)
    return dt.isoformat(timespec="microseconds") + "Z"


def parse_archive_file(
    filename: str, appliance: str | None = None
) -> Generator[dict[str, str], None, None]:
    with open(filename) as f:
        for line in f:
            stripped_line = line.strip()
            if stripped_line.startswith("#") or stripped_line == "":
                # Remove empty lines and lines that start with "#"
                continue
            values = stripped_line.split()
            pv: dict[str, Any] = {"pv": values[0]}
            # Passing samplingmethod and samplingperiod via the API
            # overwrites what is defined in the site policies.py.
            # We don't want that.
            # But we allow to force the policy
            if len(values) > 1:
                pv["policy"] = values[1]
            if appliance:
                pv["appliance"] = appliance
            yield pv


def _parse_rename_line(line: str) -> tuple[str, str] | None:
    stripped_line = line.strip()
    if stripped_line.startswith("#") or stripped_line == "":
        # Remove empty lines and lines that start with "#"
        return None
    try:
        old_name, new_name = stripped_line.split()
        return (old_name, new_name)
    except ValueError:
        LOG.error(
            f"Skipping: {stripped_line}. Invalid format, must be OLDNAME NEWNAME."
        )
        return None


def parse_rename_file(filename: str) -> Generator[tuple, None, None]:
    with open(filename) as f:
        for line in f:
            if parsed_line := _parse_rename_line(line):
                yield parsed_line


def get_pvs_from_files(
    files: list[str], appliance: str | None = None
) -> list[dict[str, str]]:
    """Return a list of PV (as dict) from a list of files"""
    return list(
        itertools.chain.from_iterable(
            [parse_archive_file(filename, appliance) for filename in files]
        )
    )


def get_rename_pvs_from_files(files: list[str]) -> list[tuple]:
    """Return a list of (current, new) PV names from a list of files"""
    return list(
        itertools.chain.from_iterable(
            [parse_rename_file(filename) for filename in files]
        )
    )


def check_result(result: dict[str, str], default_message: str | None = None) -> bool:
    """Check a result returned by the Archiver Appliance

    Return True if the status is ok
    Return False otherwise and print the default_message or validation value
    """
    status = result.get("status", "nok")
    if status.lower() != "ok":
        message = result.get("validation", default_message)
        LOG.error(f"{message}\n")
        return False
    return True
