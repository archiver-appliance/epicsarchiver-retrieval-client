"""Module for the retrieval processors."""

from __future__ import annotations

import enum
from dataclasses import dataclass


class ProcessorName(str, enum.Enum):
    """Preprocessors for data from the archiver.

    https://epicsarchiver.readthedocs.io/en/latest/user/userguide.html#processing-of-data
    """

    FIRSTSAMPLE = "firstSample"
    LASTSAMPLE = "lastSample"
    FIRSTFILL = "firstFill"
    LASTFILL = "lastFill"
    MEAN = "mean"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    NCOUNT = "ncount"
    NTH = "nth"
    MEDIAN = "median"
    STD = "std"
    JITTER = "jitter"
    IGNOREFLYERS = "ignoreflyers"
    FLYERS = "flyers"
    VARIANCE = "variance"
    POPVARIANCE = "popvariance"
    KURTOSIS = "kurtosis"
    SKEWNESS = "skewness"
    LINEAR = "linear"
    LOESS = "loess"
    OPTIMIZED = "optimized"
    OPTIMLASTSAMPLE = "optimLastSample"
    CAPLOTBINNING = "caplotbinning"
    DEADBAND = "deadBand"
    ERRORBAR = "errorbar"


@dataclass
class Processor:
    """Representation of a preprocessor."""

    processor_name: ProcessorName
    bin_size: int | None

    def calc_pv_name(self, pv: str) -> str:
        """Calculate PV Name to request from the archiver.

        Args:
            pv (str): base pv name

        Returns:
            str: the preprocessor string
        """
        if self.bin_size:
            return f"{self.processor_name.value}_{self.bin_size}({pv})"
        return f"{self.processor_name.value}({pv})"
