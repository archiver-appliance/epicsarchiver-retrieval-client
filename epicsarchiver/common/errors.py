"""This module defines custom exceptions for the archiver.

These exceptions are used to handle errors related to archiver operations.
"""

from __future__ import annotations


class ArchiverError(Exception):
    """Base class for all exceptions raised by the archiver."""


class ArchiverConnectionError(ArchiverError):
    """Exception raised when there is a connection error with the archiver."""

    def __init__(self, base_url: str, message: str | None = None):
        """Initialize the ArchiverConnectionError.

        Args:
            base_url (str): The base URL of the archiver.
            message (str | None, optional): A custom error message. Defaults to None.
        """
        self.base_url = base_url
        if message is None:
            message = f"Failed to connect to archiver at {base_url}"
        super().__init__(message)


class ArchiverResponseError(ArchiverError):
    """Exception raised when the archiver returns an unexpected response."""

    def __init__(
        self,
        base_url: str,
        url: str | None = None,
        response: str | None = None,
        message: str | None = None,
    ):
        """Initialize the ArchiverResponseError.

        Args:
            base_url (str): The base URL of the archiver.
            url (str | None, optional): The specific URL that caused the error.
                Defaults to None.
            response (str | None, optional): The response received from the archiver.
                Defaults to None.
            message (str | None, optional): A custom error message. Defaults to None.
        """
        self.base_url = base_url
        if url is None:
            url = base_url
        self.url = url
        self.response = response
        if message is None:
            message = (
                f"Received an unexpected response '{response}' "
                f"from the archiver {self.base_url} for URL: {self.url}"
            )
        super().__init__(message)
