import logging
from os import listdir
from os.path import isfile, join
from pathlib import Path

from epicsarchiver.archive_files import get_pvs_from_files
from epicsarchiver.epicsarchiver import ArchiverAppliance
from epicsarchiver.statistics.stat_responses import (
    BothArchiversResponse,
    NoConfigResponse,
)

LOG: logging.Logger = logging.getLogger(__name__)


def get_double_archived(
    archiver: ArchiverAppliance, other_archiver: ArchiverAppliance
) -> list[BothArchiversResponse]:
    """Return list of pvs archived in both archivers.

    Returns:
        list[BothArchiversResponse]: Details of pv and archivers.
    """
    return [
        BothArchiversResponse(pv, archiver.hostname, other_archiver.hostname)
        for pv in set(
            set(archiver.get_all_pvs(limit=-1)).intersection(
                set(other_archiver.get_all_pvs(limit=-1))
            )
        )
    ]


def get_not_configured(
    archiver: ArchiverAppliance, config_files: Path
) -> list[NoConfigResponse]:
    """Return list of pvs archived but not in config.

    Returns:
        list[NoConfigResponse]: Details of pvs.
    """
    onlyfiles = [
        Path(join(config_files, f))
        for f in listdir(config_files)
        if isfile(join(config_files, f)) and f.endswith(".archive")
    ]
    LOG.debug(f"CALC Not configured PVs from {archiver.hostname} and filed {onlyfiles}")
    return [
        NoConfigResponse(pv)
        for pv in set(
            set(archiver.get_all_pvs(limit=-1))
            - {ar["pv"] for ar in get_pvs_from_files(onlyfiles)}
        )
    ]
