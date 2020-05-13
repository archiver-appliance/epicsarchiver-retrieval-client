# -*- coding: utf-8 -*-
"""Command module."""
import click
from .epicsarchiver import ArchiverAppliance


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
@click.option(
    "--appliance",
    default=None,
    help="Force PVs to be archived on the specified appliance (in a cluster)",
)
@click.argument("files", nargs=-1, type=click.Path(exists=True))
@click.pass_context
def archive(ctx, appliance, files):
    """Archive all PVs included in the files passed as parameters"""
    archiver = ctx.obj["archiver"]
    result = archiver.archive_pvs_from_files(files, appliance)
    if ctx.obj["debug"]:
        click.echo(result)


@cli.command()
@click.argument("files", nargs=-1, type=click.Path(exists=True))
@click.pass_context
def rename(ctx, files):
    """Rename all PVs included in the files passed as parameters"""
    archiver = ctx.obj["archiver"]
    archiver.rename_pvs_from_files(files, debug=ctx.obj["debug"])
