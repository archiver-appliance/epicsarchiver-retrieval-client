"""Handle parsing files of lists of PVs to submit for archiver operations."""

import itertools
import logging
from collections.abc import Generator
from pathlib import Path
from typing import Any

LOG: logging.Logger = logging.getLogger(__name__)


def parse_archive_file(
    filename: Path, appliance: str | None = None
) -> Generator[dict[str, str], None, None]:
    """Parses an archive file.

    Archive file is a list of PVs with an archive policy
    name as optional arguement.

    Args:
        filename (str): filename of archive file
        appliance (str | None, optional): archiver to archive pv in. Defaults to None.

    Yields:
        Generator[dict[str, str], None, None]: produces
        dictionary with keys {"pv", "policy", "appliance"}
    """
    with filename.open(encoding="locale") as file:
        LOG.debug("PARSE archive file %s", filename)
        for line in file:
            stripped_line = line.strip()
            if stripped_line.startswith("#") or not stripped_line:
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
    if stripped_line.startswith("#") or not stripped_line:
        # Remove empty lines and lines that start with "#"
        return None
    try:
        old_name, new_name = stripped_line.split()
    except ValueError:
        LOG.exception(
            "Skipping: %s. Invalid format, must be OLDNAME NEWNAME.", stripped_line
        )
        return None
    else:
        return old_name, new_name


def parse_rename_file(filename: Path) -> Generator[tuple[str, str], None, None]:
    """Parses a file with a list of pv as old_pv_name new_pv_name.

    Args:
        filename (str): filename of rename file

    Yields:
        Generator[tuple[str, str], None, None]: produces a pair old_pv_name, new_pv_name
    """
    with filename.open(encoding="locale") as f:
        for line in f:
            if parsed_line := _parse_rename_line(line):
                yield parsed_line


def get_pvs_from_files(
    files: list[Path], appliance: str | None = None
) -> list[dict[str, str]]:
    """Return a list of PV (as dict) from a list of files."""
    return list(
        itertools.chain.from_iterable([
            parse_archive_file(filename, appliance) for filename in files
        ])
    )


def get_rename_pvs_from_files(files: list[str] | list[Path]) -> list[tuple[str, str]]:
    """Return a list of (current, new) PV names from a list of files."""
    return list(
        itertools.chain.from_iterable([
            parse_rename_file(Path(filename)) for filename in files
        ])
    )
