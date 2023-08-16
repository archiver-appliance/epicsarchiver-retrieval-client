"""Command module."""
import logging

import click
from rich.logging import RichHandler

from epicsarchiver.epicsarchiver import ArchiverAppliance

LOG: logging.Logger = logging.getLogger(__name__)


def _handle_debug(
    _ctx: click.core.Context | None,
    _param: click.core.Option | click.core.Parameter | None,
    debug: bool | int | str,
) -> bool | int | str:
    """Turn on DEBUG logs, if asked otherwise INFO default"""
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


def common_options(fn):  # type: ignore[no-untyped-def]
    """Adds multiple common options for all subcommands. Including debug flag
    and an output folder.

    Args:
        fn: The function to add the common options to.
    """
    return click.option(
        "--debug",
        is_flag=True,
        callback=_handle_debug,
        show_default=True,
        help="Turn on debug logging",
    )(fn)


@click.group()
@click.version_option()
@click.option(
    "--hostname",
    default="localhost",
    type=str,
    help="Achiver Appliance hostname or IP [default: localhost]",
)
@click.pass_context
def cli(ctx: click.core.Context, hostname: str) -> None:
    """Command line tool for interacting with the archiver."""
    ctx.obj = {"archiver": ArchiverAppliance(hostname)}


@common_options
@cli.command()
@click.option(
    "--appliance",
    default=None,
    type=str,
    help="Force PVs to be archived on the specified appliance (in a cluster)",
)
@click.argument("files", nargs=-1, type=click.Path(exists=True))
@click.pass_context
def archive(
    ctx: click.core.Context,
    appliance: str,
    files: list[str],
    debug: bool,  # noqa: FBT001, ARG001
) -> None:
    """Archive all PVs included in the files passed as parameters.

    The files shall be in CSV format (space separated) and include one PV name per line.
    A file can also include the name of the policy to force (optional).
    Empty lines and lines starting with "#" (comments) are allowed.

    Here is an example::

        # PV name    Policy
        ISrc-010:PwrC-CoilPS-01:CurS
        ISrc-010:PwrC-CoilPS-01:CurR slow
        # Comments are allowed
        LEBT-010:Vac-VCG-30000:PrsStatR


    The "slow" policy will be forced for the second PV.
    Check the help for more information.
    """
    archiver: ArchiverAppliance = ctx.obj["archiver"]
    res = archiver.archive_pvs_from_files(files, appliance)
    LOG.debug(res)
    ctx.exit(0)


@common_options
@cli.command()
@click.argument(
    "files",
    nargs=-1,
    type=click.Path(exists=True),
)
@click.pass_context
def rename(
    ctx: click.core.Context,
    files: list[str],
    debug: bool,  # noqa: FBT001, ARG001
) -> None:
    """Rename all PVs included in the files passed as parameters.

    Each PV will be paused, renamed and resumed. The old name remains paused.

    .. code-block:: console

        epicsarchiver --hostname archiver-01.example.com rename file1 file2

    The files shall be in CSV format (space separated) and include the current PV name
    and the new one.
    Empty lines and lines starting with "#" (comments) are allowed.

    Here is an example::

        # PV current name                 new name
        ISrc-010:PwrC-CoilPS-01:CurS ISrc-010:PwrC-CoilPS-02:CurS
        ISrc-010:PwrC-CoilPS-01:CurR ISrc-010:PwrC-CoilPS-02:CurR
        # Comments are allowed
        LEBT-010:Vac-VCG-30000:PrsStatR LEBT-010:Vac-VCG-30001
    """
    archiver: ArchiverAppliance = ctx.obj["archiver"]
    archiver.rename_pvs_from_files(files)
    ctx.exit(0)
