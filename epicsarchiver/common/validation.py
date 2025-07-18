"""Validation functions and exceptions for archiver retrieval."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import datetime

    from epicsarchiver.retrieval.archiver_retrieval.processor import Processor


class ValidationError(Exception):
    """Base class for all validation-related exceptions."""


class PVNameError(ValidationError):
    """Exception raised for invalid PV names."""

    def __init__(self, pv: str) -> None:
        """Initialize the PVNameError with a specific message.

        Args:
            pv (str): The process variable name that caused the error.
        """
        super().__init__(f"PV '{pv}' must be a non-empty string.")


def validate_pv(pv: str) -> None:
    """Validate the PV name.

    Args:
        pv (str): The process variable name to validate.

    Raises:
        PVNameError: If the PV name is empty or not a string.
    """
    if not pv:
        raise PVNameError(pv)


class TimePeriodError(ValidationError):
    """Exception raised for invalid time periods."""

    def __init__(self, start: datetime.datetime, end: datetime.datetime) -> None:
        """Initialize the TimePeriodError with a specific message.

        Args:
            start (datetime.datetime): Start Time of the period.
            end (datetime.datetime): End Time of the period.
        """
        super().__init__(f"Start time {start} must be before end time {end}.")


def validate_start_end(start: datetime.datetime, end: datetime.datetime) -> None:
    """Validate the start and end datetime objects.

    Args:
        start (datetime.datetime): The start time of the period.
        end (datetime.datetime): The end time of the period.

    Raises:
        TimePeriodError: If the start time is not before the end time.
    """
    if start > end:
        raise TimePeriodError(start, end)


class ProcessorBinSizeError(ValidationError):
    """Exception raised for invalid processor bin size."""

    def __init__(self, bin_size: int) -> None:
        """Initialize the ProcessorBinSizeError with a specific message.

        Args:
            bin_size (int): The bin size that caused the error.
        """
        super().__init__(
            f"Processor's bin_size must be an integer greater than 1, got {bin_size}."
        )


def validate_processor(processor: Processor | None) -> None:
    """Validate the processor.

    Args:
        processor (Processor | None): The processor to validate.

    Raises:
        ProcessorBinSizeError: If the processor's bin_size is not an
          integer greater than 1.
    """
    if processor is None:
        return

    if processor and processor.bin_size is not None and processor.bin_size <= 1:
        raise ProcessorBinSizeError(processor.bin_size)
