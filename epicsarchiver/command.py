"""Command module."""

import logging

import click

from epicsarchiver.epicsarchiver import ArchiverAppliance
from epicsarchiver.retrieval import command as retrieval

LOG: logging.Logger = logging.getLogger(__name__)


@click.group()
@click.version_option()
@click.option(
    "--hostname",
    "-h",
    default="localhost",
    type=str,
    envvar="EPICSARCHIVER_HOSTNAME",
    help="Achiver Appliance hostname or IP [default: localhost]",
)
@click.pass_context
def cli(ctx: click.core.Context, hostname: str) -> None:
    """Command line tool for interacting with the archiver."""
    ctx.obj = {"archiver": ArchiverAppliance(hostname)}


cli.add_command(retrieval.get)
