"""Possible Statistics found from the Archiver and related services."""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from epicsarchiver.statistics.models.stat_responses import BaseStatResponse


class Stat(str, enum.Enum):
    """List of statistics from the archiver.

    Args:
        enum (Stat): A statistic on pvs in archiver
    """

    BufferOverflow = "PV updating faster than the sampling period."
    TypeChange = "PV changed type, which archiver hasn't been updated for."
    IncorrectTimestamp = "PV loses events due to incorrect timestamps."
    SlowChanging = "More events lost than stored."
    DisconnectedPVs = "PV disconnected for a long time."
    SilentPVs = "Never received a valid event."
    DoubleArchived = "Archived in both clusters."
    StorageRates = "In the top storage rates."
    LostConnection = "In the top dropped connections."
    NotConfigured = "PV archived, but not in config."
    InvalidName = "PV has name that should not be archived"


@dataclass
class PVStats:
    """Statistics of a PV.

    name: PV Name
    stats: Dictionary of Statistic type to BaseStatResponse with more details.
    """

    name: str
    stats: dict[Stat, BaseStatResponse]
