"""Shared Command methods module."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rich.logging import RichHandler

if TYPE_CHECKING:
    import click

LOG: logging.Logger = logging.getLogger(__name__)


def handle_debug(
    _ctx: click.core.Context | None,
    _param: click.core.Option | click.core.Parameter | None,
    debug: bool | int | str,  # noqa: FBT001
) -> bool | int | str:
    """Turn on DEBUG logs, if asked otherwise INFO default."""
    format_msg = "%(message)s"

    if debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format=format_msg,
            datefmt="[%X]",
            handlers=[RichHandler(rich_tracebacks=True)],
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format=format_msg,
            datefmt="[%X]",
            handlers=[RichHandler()],
        )
    return debug
