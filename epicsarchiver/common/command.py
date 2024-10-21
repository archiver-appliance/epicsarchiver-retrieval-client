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
    """Turn on DEBUG logs, if asked otherwise INFO default.

    Args:
        _ctx (click.core.Context | None): click context
        _param (click.core.Option | click.core.Parameter | None): click paramters
            to pass through
        debug (bool | int | str): debug note

    Returns:
        bool | int | str):  debug passed through
    """
    format_msg = "%(message)s"

    if debug:
        level = logging.DEBUG
        tracebacks = True
    else:
        level = logging.INFO
        tracebacks = False

    logging.basicConfig(
        level=level,
        format=format_msg,
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=tracebacks)],
    )
    return debug
