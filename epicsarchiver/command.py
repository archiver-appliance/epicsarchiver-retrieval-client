# -*- coding: utf-8 -*-
"""Command module."""
import click
from . import ArchiverAppliance


@click.group()
@click.version_option()
@click.option(
    "--hostname",
    default="localhost",
    help="Achiver Appliance hostname or IP [default: localhost]",
)
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.pass_context
def cli(ctx, hostname, debug):
    ctx.obj = {"archiver": ArchiverAppliance(hostname), "debug": debug}


@cli.command()
@click.argument("files", nargs=-1, type=click.Path(exists=True))
@click.option(
    "--period",
    default="1",
    help="Sampling period in seconds to use if not provided in the archive file [default: 1]",
)
@click.option(
    "--method",
    default="MONITOR",
    type=click.Choice(["MONITOR", "SCAN"]),
    help="Sampling method to use if not provided in the archive file [default: MONITOR]",
)
@click.pass_context
def archive(ctx, period, method, files):
    """Archive all PVs included in the files passed as parameters"""
    archiver = ctx.obj["archiver"]
    result = archiver.archive_pvs_from_files(files, period, method)
    if ctx.obj["debug"]:
        click.echo(result)
