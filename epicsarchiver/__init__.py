# -*- coding: utf-8 -*-
"""Top-level package for Python EPICS Archiver Appliance library."""
from pkg_resources import get_distribution, DistributionNotFound
try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    pass

__author__ = """Benjamin Bertrand"""
__email__ = 'benjamin.bertrand@esss.se'


from .epicsarchiver import ArchiverAppliance
