"""Shared utilities across the other modules."""

from enum import Enum


class ArchDbrType(Enum):
    """List of Dbr Types that the archiver uses."""

    DBR_SCALAR_STRING = 0
    DBR_SCALAR_SHORT = 1
    DBR_SCALAR_FLOAT = 2
    DBR_SCALAR_ENUM = 3
    DBR_SCALAR_BYTE = 4
    DBR_SCALAR_INT = 5
    DBR_SCALAR_DOUBLE = 6
    DBR_WAVEFORM_STRING = 7
    DBR_WAVEFORM_SHORT = 8
    DBR_WAVEFORM_FLOAT = 9
    DBR_WAVEFORM_ENUM = 10
    DBR_WAVEFORM_BYTE = 11
    DBR_WAVEFORM_INT = 12
    DBR_WAVEFORM_DOUBLE = 13
    DBR_V4_GENERIC_BYTES = 14
