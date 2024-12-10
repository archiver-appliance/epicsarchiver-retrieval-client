"""Shared utilities across the other modules."""

from enum import Enum, auto


class ArchDbrType(Enum):
    """List of Dbr Types that the archiver uses."""

    DBR_SCALAR_STRING = auto()
    DBR_SCALAR_SHORT = auto()
    DBR_SCALAR_FLOAT = auto()
    DBR_SCALAR_ENUM = auto()
    DBR_SCALAR_BYTE = auto()
    DBR_SCALAR_INT = auto()
    DBR_SCALAR_DOUBLE = auto()
    DBR_WAVEFORM_STRING = auto()
    DBR_WAVEFORM_SHORT = auto()
    DBR_WAVEFORM_FLOAT = auto()
    DBR_WAVEFORM_ENUM = auto()
    DBR_WAVEFORM_BYTE = auto()
    DBR_WAVEFORM_INT = auto()
    DBR_WAVEFORM_DOUBLE = auto()
    DBR_V4_GENERIC_BYTES = auto()
